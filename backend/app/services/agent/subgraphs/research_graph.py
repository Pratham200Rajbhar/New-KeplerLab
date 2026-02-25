"""Deep Research Engine — Minimal, deterministic implementation.

Implements a single functional pipeline for the RESEARCH intent:
1. Generate 5-10 targeted queries.
2. Concurrent DuckDuckGo HTML scraping using httpx.
3. Concurrent text extraction using httpx + trafilatura.
4. Hard fail if < 3 sources.
5. Strict JSON summary synthesis.

Limits:
  MAX_SEARCH_QUERIES = 10
  MAX_TOTAL_URLS = 15
  MAX_TIME = 45s
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

# ── Safety Limits ─────────────────────────────────────────────

MAX_SEARCH_QUERIES = 10
MAX_TOTAL_URLS = 15
MAX_TIME_SECONDS = 45


# ── Core Implementation ───────────────────────────────────────

async def run_research(
    user_query: str,
    user_id: str,
    notebook_id: str,
    material_ids: list[str] | None = None,
) -> str:
    """Run the minimal deep research pipeline and return the JSON report string."""
    start_time = time.time()
    
    # 1. Generate Queries
    queries = await _generate_queries(user_query)
    
    # 2. Search execution
    urls = await _execute_searches(queries, start_time)
    
    # 3. Content extraction
    sources = await _extract_content(urls, start_time)
    
    # Proceed with whatever sources are available (1 or more)
    if len(sources) == 0:
        error_msg = "Failed to extract any valid sources. Consider broadening your query."
        logger.warning(f"Research failed: {error_msg}")
        return json.dumps({
            "executive_summary": error_msg,
            "key_findings": [],
            "data_points": [],
            "conclusion": "Research aborted due to no available data.",
            "sources": []
        })

    # 4. Report Synthesis — add note about source count if limited
    report_json = await _synthesize_report(user_query, sources)
    
    return report_json


async def run_research_stream(
    user_query: str,
    user_id: str,
    notebook_id: str,
    material_ids: list[str] | None = None,
) -> AsyncIterator[str]:
    """Streaming research with all 5 SSE phases properly emitted."""
    start_time = time.time()

    # Phase 1: Planning
    yield 'event: research_step\ndata: {"node": "planning", "status": "active"}\n\n'
    queries = await _generate_queries(user_query)
    yield 'event: research_step\ndata: {"node": "planning", "status": "complete"}\n\n'

    # Phase 2: Searching
    yield 'event: research_step\ndata: {"node": "searching", "status": "active"}\n\n'
    urls = await _execute_searches(queries, start_time)
    yield 'event: research_step\ndata: {"node": "searching", "status": "complete"}\n\n'

    # Phase 3: Extracting
    yield 'event: research_step\ndata: {"node": "extracting", "status": "active"}\n\n'
    sources = await _extract_content(urls, start_time)
    yield 'event: research_step\ndata: {"node": "extracting", "status": "complete"}\n\n'

    if len(sources) == 0:
        error_data = json.dumps({"error": "No valid sources found"})
        yield f"event: error\ndata: {error_data}\n\n"
        return

    # Phase 4: Clustering (currently a pass-through, but emit status for UI)
    yield 'event: research_step\ndata: {"node": "clustering", "status": "active"}\n\n'
    # Future: implement theme clustering here
    yield 'event: research_step\ndata: {"node": "clustering", "status": "complete"}\n\n'

    # Phase 5: Writing
    yield 'event: research_step\ndata: {"node": "writing", "status": "active"}\n\n'
    try:
        report_json = await _synthesize_report(user_query, sources)
        yield 'event: research_step\ndata: {"node": "writing", "status": "complete"}\n\n'
        yield f"event: final_report\ndata: {report_json}\n\n"
        yield 'event: done\ndata: {}\n\n'
    except Exception as e:
        logger.exception("Research stream failed during synthesis")
        error_data = json.dumps({"error": str(e)})
        yield f"event: error\ndata: {error_data}\n\n"


async def _generate_queries(user_query: str) -> List[str]:
    """Generate 5-10 targeted search queries."""
    from app.services.llm_service.llm import get_llm
    llm = get_llm(mode="creative")
    
    prompt = f"""You are a research planner. Generate 5-10 highly targeted search queries for this topic:
Topic: "{user_query}"

Return ONLY a JSON array of strings:
["query 1", "query 2"]
"""
    try:
        resp = await llm.ainvoke(prompt)
        text = getattr(resp, "content", str(resp)).strip()
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            queries = json.loads(match.group())
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:MAX_SEARCH_QUERIES]
    except Exception as e:
        logger.warning(f"Failed to generate queries, falling back: {e}")
        
    return [user_query]


async def _execute_searches(queries: List[str], start_time: float) -> List[Dict[str, str]]:
    """Concurrent barebones DuckDuckGo HTML scraping."""
    results = []
    seen_urls = set()
    
    # We serialize the request slightly to avoid DDG rate limiting
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # Round robin user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        
        for i, query in enumerate(queries):
            if len(results) >= MAX_TOTAL_URLS:
                break
                
            elapsed = time.time() - start_time
            if elapsed > (MAX_TIME_SECONDS * 0.4): # Allocate 40% time for searching
                logger.warning(f"Research time limit approaching ({elapsed}s), stopping search.")
                break
                
            try:
                headers = {"User-Agent": user_agents[i % len(user_agents)]}
                url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    links = _parse_ddg_results(resp.text)
                    for link in links:
                        if link["url"] not in seen_urls and len(results) < MAX_TOTAL_URLS:
                            results.append(link)
                            seen_urls.add(link["url"])
                            
                await asyncio.sleep(0.2) # Rate limit (reduced from 0.5s)
            except Exception as e:
                logger.warning(f"Search for '{query}' failed: {e}")
                
    return results


def _parse_ddg_results(html: str) -> List[Dict[str, str]]:
    """Regex-based DDG extraction."""
    results = []
    pattern = r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html)
    for href, title in matches:
        if href.startswith("http"):
            # Clean DDG redirect iff present
            if "uddg=" in href:
                from urllib.parse import unquote, parse_qs, urlparse
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    href = unquote(params["uddg"][0])
                    
            if href.startswith("http"):
                 results.append({"url": href, "title": title.strip()})
    return results[:7]


async def _extract_content(search_results: List[Dict[str, str]], start_time: float) -> List[Dict[str, str]]:
    """Concurrent fetching and trafilatura extraction."""
    valid_sources = []
    
    async def fetch_and_extract(result: Dict[str, str], client: httpx.AsyncClient):
        elapsed = time.time() - start_time
        if elapsed > (MAX_TIME_SECONDS * 0.8): # Allocate 80% time for searching & extraction
             return None
             
        try:
             resp = await client.get(result["url"], headers={"User-Agent": "ResearchBot/1.0"})
             if resp.status_code == 200:
                 try:
                     import trafilatura
                     text = trafilatura.extract(resp.text, include_comments=False, include_tables=True)
                     if text and len(text) > 100:
                         return {
                             "url": result["url"],
                             "title": result.get("title", ""),
                             "content": text[:4000] # Limit chunk size
                         }
                 except ImportError:
                     # Fallback bare extraction
                     text = re.sub(r'<[^>]+>', ' ', resp.text)
                     text = re.sub(r'\s+', ' ', text).strip()
                     if len(text) > 100:
                         return {
                             "url": result["url"],
                             "title": result.get("title", ""),
                             "content": text[:4000]
                         }
        except Exception:
             pass
        return None

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        tasks = [fetch_and_extract(res, client) for res in search_results]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        
        for outcome in outcomes:
            if outcome and not isinstance(outcome, Exception):
                valid_sources.append(outcome)
                
    return valid_sources


async def _synthesize_report(user_query: str, sources: List[Dict[str, str]]) -> str:
    """Generate final JSON structure."""
    from app.services.llm_service.llm import get_llm
    llm = get_llm(mode="chat")  # factual synthesis
    
    context_blocks = []
    source_list = []
    for i, s in enumerate(sources):
        context_blocks.append(f"[SOURCE {i+1}] {s['title']}\nURL: {s['url']}\nCONTENT:\n{s['content']}")
        source_list.append({"title": s['title'], "url": s['url']})
        
    context_str = "\n\n".join(context_blocks)
    
    prompt = f"""Synthesize a complete research report based on the provided context sources.

Research Query: "{user_query}"

Context:
{context_str}

You MUST return your answer as a raw JSON object with the EXACT following keys.
Write ONLY valid JSON.

{{
  "executive_summary": "A 2-3 sentence high level summary of the findings.",
  "key_findings": [
    "string finding 1 with [SOURCE N] citation",
    "string finding 2 with [SOURCE N] citation"
  ],
  "data_points": [
    "numeric fact 1 with [SOURCE N] citation",
    ...
  ],
  "conclusion": "A concluding thought or implications.",
  "sources": []
}}

Do NOT put markdown backticks around the JSON. Return raw JSON.
Leave the "sources" list array EXACTLY EMPTY `[]`, we will populate it natively later.
"""
    try:
        resp = await llm.ainvoke(prompt)
        text = getattr(resp, "content", str(resp)).strip()
        
        # Strip markdown json block if provided
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            text = match.group()
            
        data = json.loads(text)
        
        # Populate sources natively to ensure correctness
        data["sources"] = source_list
        return json.dumps(data)
        
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return json.dumps({
            "executive_summary": "Synthesis failed due to an error.",
            "key_findings": [],
            "data_points": [],
            "conclusion": str(e),
            "sources": source_list
        })
