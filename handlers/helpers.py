# utils/helpers.py
import requests
import json

def safe_request(method, url, **kwargs):
    """
    Wrapper around requests to centralize timeouts, error handling.
    Returns parsed JSON if possible, else raw text.
    """
    timeout = kwargs.pop("timeout", 20)
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        resp.raise_for_status()
        # try parse json
        try:
            return resp.json()
        except Exception:
            return resp.text
    except Exception as e:
        # For now, print and re-raise for calling code to decide fallback
        print(f"[safe_request] error calling {url}: {e}")
        raise

def truncate_text(text: str, max_len: int = 1000) -> str:
    if not text:
        return ""
    return text[:max_len]
