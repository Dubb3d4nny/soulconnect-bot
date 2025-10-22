# handlers/journaling.py
# Light stub for journaling. For bishop demo, we keep journaling opt-in and private.
import os
import json
from datetime import datetime

JOURNAL_DIR = os.getenv("JOURNAL_DIR", "journals")
os.makedirs(JOURNAL_DIR, exist_ok=True)

def save_journal(user_id: int, text: str) -> str:
    filename = os.path.join(JOURNAL_DIR, f"{user_id}.jsonl")
    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    with open(filename, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return filename
