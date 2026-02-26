import ipaddress
import os
import re
import socket
from urllib.parse import urlparse, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from typing import Optional
import logging

from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────────────────

# Headers to strip so files / pages can be embedded in an iframe
RESTRICTED_HEADERS = {
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "strict-transport-security",
    "x-xss-protection",
    "x-content-type-options",
}

# Private / loopback CIDR ranges (SSRF protection)
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
]

# Office file extensions that should use MS Office Online Viewer
OFFICE_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp"}

# Extensions we will proxy directly with Content-Disposition: inline
INLINE_EXTENSIONS = {".pdf"}

# All viewable extensions (file viewer page will handle)
VIEWABLE_EXTENSIONS = INLINE_EXTENSIONS | OFFICE_EXTENSIONS | {".txt", ".csv", ".md", ".rtf"}

# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_url(url: str) -> str:
    """
    Parse, validate and normalise a file URL.
    Raises HTTPException 400 for disallowed URLs.
    Returns the cleaned URL string.
    """
    # Must be HTTPS only (no http, no ftp, no javascript: etc.)
    if not url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Only HTTPS URLs are allowed.",
        )

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: missing hostname.")

    # Reject localhost variants
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise HTTPException(status_code=400, detail="Access to local addresses is not allowed.")

    # Reject numeric IPs that fall in private ranges (SSRF protection)
    try:
        ip = ipaddress.ip_address(hostname)
        if any(ip in net for net in _PRIVATE_NETWORKS):
            raise HTTPException(status_code=400, detail="Access to private network addresses is not allowed.")
    except ValueError:
        # Not a numeric IP — try DNS resolution check
        try:
            resolved_ip = ipaddress.ip_address(socket.getaddrinfo(hostname, None)[0][4][0])
            if any(resolved_ip in net for net in _PRIVATE_NETWORKS):
                raise HTTPException(status_code=400, detail="Resolved IP is in a private range.")
        except (socket.gaierror, OSError):
            pass  # DNS failure will surface as a 502 later

    return url


def _detect_file_type(url: str) -> dict:
    """Return metadata about the viewable file type from its URL path."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    ext = os.path.splitext(path)[1]
    filename = os.path.basename(parsed.path) or "file"

    if ext in INLINE_EXTENSIONS:
        kind = "pdf"
    elif ext in OFFICE_EXTENSIONS:
        kind = "office"
    elif ext in {".txt", ".csv", ".md", ".rtf"}:
        kind = "text"
    else:
        kind = "other"

    return {"kind": kind, "ext": ext, "filename": filename}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/proxy")
async def proxy_webpage(
    url: str = Query(..., description="URL to proxy"),
    current_user=Depends(get_current_user),
):
    """
    Fetches a webpage and strips headers that prevent iframe embedding.
    Requires authentication. Only HTTPS URLs are allowed (SSRF protection).
    """
    # Validate URL — enforce HTTPS and block private networks
    url = _validate_url(url)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "text/html")

            proxy_headers = {}
            for name, value in response.headers.items():
                name_lower = name.lower()
                if name_lower not in RESTRICTED_HEADERS and name_lower not in {"content-encoding", "transfer-encoding"}:
                    proxy_headers[name] = value

            return Response(content=response.content, status_code=response.status_code, media_type=content_type, headers=proxy_headers)

    except httpx.RequestError as e:
        logger.error(f"Error proxying {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Unable to reach {url}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error proxying {url}: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from target server: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error proxying {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/file-viewer/info")
async def file_viewer_info(url: str = Query(..., description="Public HTTPS file URL")):
    """
    Validate a public file URL and return viewer metadata.
    Tells the frontend which viewer strategy to use (pdf / office / text / other).
    Also provides the MS Office Online Viewer embed URL for office documents.
    """
    url = _validate_url(url)
    meta = _detect_file_type(url)

    result = {
        "url": url,
        "kind": meta["kind"],
        "ext": meta["ext"],
        "filename": meta["filename"],
    }

    if meta["kind"] == "office":
        encoded = quote(url, safe="")
        result["office_viewer_url"] = f"https://view.officeapps.live.com/op/embed.aspx?src={encoded}"

    return JSONResponse(content=result)


@router.get("/file-viewer/proxy")
async def file_viewer_proxy(url: str = Query(..., description="Public HTTPS PDF/text URL")):
    """
    Proxy a PDF or plain-text file and serve it with Content-Disposition: inline
    so the browser renders it directly instead of forcing a download.
    Only allows HTTPS non-private URLs.
    """
    url = _validate_url(url)
    meta = _detect_file_type(url)

    if meta["kind"] not in ("pdf", "text"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and plain-text files can be proxied. Use the Office Online Viewer for office documents.",
        )

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "application/octet-stream")

            # Force content-type for known types so the browser doesn't sniff
            if meta["ext"] == ".pdf":
                content_type = "application/pdf"

            filename_safe = re.sub(r"[^\w.\-]", "_", meta["filename"])

            return Response(
                content=response.content,
                status_code=200,
                media_type=content_type,
                headers={
                    # inline = render in browser, not save
                    "Content-Disposition": f'inline; filename="{filename_safe}"',
                    # Allow the frontend to embed this in an iframe
                    "X-Frame-Options": "SAMEORIGIN",
                    "Access-Control-Allow-Origin": "*",
                },
            )

    except httpx.RequestError as e:
        logger.error(f"file_viewer_proxy error for {url}: {e}")
        raise HTTPException(status_code=502, detail="Unable to fetch the file. Check the URL and try again.")
    except httpx.HTTPStatusError as e:
        logger.error(f"file_viewer_proxy HTTP error for {url}: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Remote server returned {e.response.status_code}.")
    except Exception as e:
        logger.error(f"file_viewer_proxy unexpected error for {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
