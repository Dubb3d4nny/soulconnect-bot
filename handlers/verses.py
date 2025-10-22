# handlers/verses.py
import random

# small curated verse list as example — expand later or integrate Bible API
VERSES = [
    "Psalm 46:1 — 'God is our refuge and strength.'",
    "Philippians 4:6-7 — 'Do not be anxious about anything...' ",
    "Isaiah 41:10 — 'Fear not, for I am with you.'",
    "Psalm 23:1 — 'The Lord is my shepherd; I shall not want.'"
]

def get_daily_verse() -> str:
    # simple random verse for now; could be deterministic by date
    return random.choice(VERSES)
