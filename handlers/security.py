# utils/security.py
import os
import time
from collections import defaultdict
from functools import wraps

# Rate limiting: simple in-memory leaky bucket (per-user)
RATE_LIMIT_CONFIG = {
    "messages_per_minute": int(os.getenv("MSG_PER_MIN", "10")),
    "audio_per_minute": int(os.getenv("AUDIO_PER_MIN", "2"))
}

_user_timestamps = defaultdict(list)

def rate_limit_check(user_id: int, kind="message") -> bool:
    """
    Very simple per-user rate limiter.
    kind: 'message' or 'audio'
    returns True if allowed, False if rate limited.
    """
    now = time.time()
    window = 60
    max_calls = RATE_LIMIT_CONFIG["messages_per_minute"] if kind == "message" else RATE_LIMIT_CONFIG["audio_per_minute"]
    timestamps = _user_timestamps[(user_id, kind)]
    # remove old
    _user_timestamps[(user_id, kind)] = [t for t in timestamps if now - t < window]
    if len(_user_timestamps[(user_id, kind)]) >= max_calls:
        return False
    _user_timestamps[(user_id, kind)].append(now)
    return True

# Admin list — set as env var ADMIN_IDS="12345,67890"
def is_admin(user_id: int) -> bool:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw:
        return False
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        return int(user_id) in ids
    except Exception:
        return False

def sanitize_text(text: str) -> str:
    # Basic sanitization; extend as needed
    if not text:
        return ""
    return text.strip()
