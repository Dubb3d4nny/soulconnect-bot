# bot.py

import os
import random
import requests
import tempfile
import threading
import subprocess
import time
import logging
from collections import defaultdict
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
ApplicationBuilder, CommandHandler,
MessageHandler, ContextTypes, filters
)
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
from responses import get_response
from handlers.verses import get_daily_verse

# ---------- INIT ----------

load_dotenv()
logging.basicConfig(
level=logging.INFO,
format="%(asctime)s [%(levelname)s] %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
raise RuntimeError("BOT_TOKEN is required in .env file")

# ---------- FASTAPI ----------

app = FastAPI()

@app.get("/", methods=["GET", "HEAD"])
def home():
return {"message": "🕊️ SoulConnect running."}

@app.get("/heartbeat", methods=["GET", "HEAD"])
def heartbeat():
return {"status": "💓 alive"}

# ---------- RATE LIMITER ----------

RATE = {
"messages_per_minute": int(os.getenv("MSG_PER_MIN", "20")),
"audio_per_minute": int(os.getenv("AUDIO_PER_MIN", "3"))
}
_user_calls = defaultdict(list)

def rate_limited(user_id: int, kind: str = "message") -> bool:
now = time.time()
window = 60
max_calls = RATE["messages_per_minute"] if kind == "message" else RATE["audio_per_minute"]
key = (user_id, kind)
calls = [t for t in _user_calls[key] if now - t < window]
_user_calls[key] = calls
if len(calls) >= max_calls:
return False
_user_calls[key].append(now)
return True

# ---------- HELPERS ----------

@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def safe_hf_post(url: str, headers=None, json=None, data=None, timeout=30):
try:
resp = requests.post(url, headers=headers or {}, json=json, data=data, timeout=timeout)
resp.raise_for_status()
try:
return resp.json()
except Exception:
return resp.text
except Exception as e:
logging.warning(f"[safe_hf_post] Retrying due to error: {e}")
raise

def convert_to_wav(input_path: str) -> str:
out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
out_path = out.name
out.close()
cmd = ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", out_path]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
return out_path

# ---------- HUGGING FACE HELPERS ----------

EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
GODEL_MODEL = "microsoft/GODEL-v1_1-large-seq2seq"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-small")

def detect_emotion(text: str) -> str:
if not text:
return "neutral"
try:
url = f"[https://api-inference.huggingface.co/models/{EMOTION_MODEL}](https://api-inference.huggingface.co/models/{EMOTION_MODEL})"
res = safe_hf_post(url, headers=HEADERS, json={"inputs": text}, timeout=15)
if isinstance(res, list) and res:
data = res[0]
label = None
if isinstance(data, list):
label = max(data, key=lambda x: x["score"])["label"].lower()
elif isinstance(data, dict):
label = data.get("label", "neutral").lower()
if "sad" in label: return "sadness"
if "fear" in label: return "fear"
if "joy" in label: return "joy"
if "anger" in label: return "anger"
return "neutral"
except Exception as e:
logging.error(f"[detect_emotion] error: {e}")
return "neutral"

def generate_reflection(user_text: str) -> str:
if not user_text:
return "💭 God understands even the words you can’t speak. You’re loved."
try:
url = f"[https://api-inference.huggingface.co/models/{GODEL_MODEL}](https://api-inference.huggingface.co/models/{GODEL_MODEL})"
prompt = (
"Instruction: be an empathetic Christian friend who gives faith-based encouragement.\n"
f"Input: {user_text}\nOutput:"
)
payload = {"inputs": prompt, "options": {"max_new_tokens": 150}}
res = safe_hf_post(url, headers=HEADERS, json=payload, timeout=45)
text = ""
if isinstance(res, list) and res:
text = res[0].get("generated_text", "")
elif isinstance(res, dict):
text = res.get("generated_text", "") or res.get("text", "")
return (text or "").strip() or "📖 Psalm 46:1 — 'God is our refuge and strength.'"
except Exception as e:
logging.error(f"[generate_reflection] error: {e}")
return "💭 God understands even the words you can’t speak. You’re loved."

def speech_to_text(file_path: str) -> str:
try:
if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
return ""
wav_path = convert_to_wav(file_path)
with open(wav_path, "rb") as f:
data = f.read()
url = f"[https://api-inference.huggingface.co/models/{WHISPER_MODEL}](https://api-inference.huggingface.co/models/{WHISPER_MODEL})"
res = safe_hf_post(url, headers=HEADERS, data=data, timeout=60)
if isinstance(res, dict):
return res.get("text") or res.get("transcription") or ""
return ""
except Exception as e:
logging.error(f"[speech_to_text] error: {e}")
return ""

# ---------- TELEGRAM BOT ----------

tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"🕊️ Welcome to SoulConnect — a safe place for your soul.\n"
"Tell me what's on your heart today.\n\nSend text, voice notes, or video notes."
)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
user_id = user.id if user else None
text = (update.message.text or "").strip()

```
if user_id and not rate_limited(user_id, "message"):
    await update.message.reply_text("⚠️ You’re sending messages too quickly. Please wait a moment.")
    return

if text.lower().strip() in ("/start", "start"):
    return await start(update, context)
if text.lower().strip() in ("/verse", "verse"):
    verse = get_daily_verse()
    await update.message.reply_text(verse)
    return

emotion = detect_emotion(text)
reflection = generate_reflection(text)
verse = get_daily_verse()
combo = f"{reflection}\n\n{get_response(emotion)}\n\n{verse}"
await update.message.reply_text(combo)
```

async def handle_audio_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
user_id = user.id if user else None

```
if user_id and not rate_limited(user_id, "audio"):
    await update.message.reply_text("⚠️ You’re sending audio too quickly. Please wait a moment.")
    return

file_obj = update.message.voice or update.message.video_note or update.message.audio
if not file_obj:
    await update.message.reply_text("🎧 Couldn't find audio in that message.")
    return

tmp_path = None
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        await file_obj.get_file().download_to_drive(tmp.name)
        tmp_path = tmp.name
except Exception as e:
    logging.error(f"[handle_audio_like] download error: {e}")
    await update.message.reply_text("⚠️ Error downloading audio. Please try again.")
    return

transcript = speech_to_text(tmp_path)
try:
    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)
except Exception:
    pass

if not transcript:
    await update.message.reply_text("🎧 Couldn't hear clearly, please try again or record a short voice note.")
    return

emotion = detect_emotion(transcript)
reflection = generate_reflection(transcript)
verse = get_daily_verse()
reply = f"{reflection}\n\n{get_response(emotion)}\n\n{verse}"
await update.message.reply_text(reply)
```

# ---------- REGISTER ----------

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
tg_app.add_handler(MessageHandler(filters.VOICE | filters.VIDEO_NOTE | filters.AUDIO, handle_audio_like))

# ---------- MAIN ----------

if **name** == "**main**":
import uvicorn
def start_api():
uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

```
threading.Thread(target=start_api, daemon=True).start()
logging.info("✅ SoulConnect heartbeat active.")
tg_app.run_polling()
```
