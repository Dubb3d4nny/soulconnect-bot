# handlers/verses.py
import random
import requests

# some common books to pick from randomly
BOOKS = [
    "John", "Psalms", "Proverbs", "Romans", "Isaiah",
    "Matthew", "Mark", "Luke", "Philippians", "1 Corinthians"
]

def get_daily_verse() -> str:
    """Fetch a random verse from the Bible API with graceful fallback."""
    book = random.choice(BOOKS)
    chapter = random.randint(1, 5)
    verse = random.randint(1, 10)
    url = f"https://bible-api.com/{book}%20{chapter}:{verse}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        text = data.get("text", "").strip()
        ref = data.get("reference", f"{book} {chapter}:{verse}")
        if text:
            return f"📖 {ref} — \"{text}\""
        else:
            return "📖 The Word of God brings peace to those who seek Him. ✨"
    except Exception:
        # fallback verse if API fails
        return "📖 Isaiah 40:8 — 'The grass withers, the flower fades, but the word of our God will stand forever.' 🌿"
