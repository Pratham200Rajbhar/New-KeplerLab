from typing import Any

def sanitize_null_bytes(data: Any) -> Any:
    """
    Recursively remove null bytes (x00) from strings, lists, and dictionaries.
    Postgres TEXT and VARCHAR columns do not allow null bytes.
    """
    if isinstance(data, str):
        return data.replace("\x00", "")
    elif isinstance(data, list):
        return [sanitize_null_bytes(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_null_bytes(value) for key, value in data.items()}
    else:
        return data
