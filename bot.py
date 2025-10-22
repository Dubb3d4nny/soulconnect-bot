# bot.py
import os
import random
import requests
import tempfile
import threading
import subprocess
import time
from collections import defaultdict
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from responses import get_response

# ---------- ENV ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

# ---------- FASTAPI ----------
app = FastAPI()

# Accept both GET and HEAD so UptimeRobot's HEAD checks won't get 405
@app.get("/", methods=["GET", "HEAD"])
def home():
    return {"message": "🕊️ SoulConnect running."}

@app.get("/heartbeat", methods=["GET", "HEAD"])
def heartbeat():
    return {"status": "💓 alive"}

# ---------- SIMPLE RATE LIMITER (in-memory) ----------
# Note: in-memory only — restarts reset it. Persist or use Redis for scale.
RATE = {
    "messages_per_minute": int(os.getenv("MSG_PER_MIN", "20")),
    "audio_per_minute": int(os.getenv("AUDIO_PER_MIN", "3"))
}
_user_calls = defaultdict(list)  # key: (user_id, kind) -> timestamps list

def rate_limited(user_id: int, kind: str = "message") -> bool:
    """Return True if allowed, False if rate limited."""
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
def safe_hf_post(url: str, headers=None, json=None, data=None, timeout=30):
    """Simple wrapper for Hugging Face calls."""
    try:
        resp = requests.post(url, headers=headers or {}, json=json, data=data, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text
    except Exception as e:
        print(f"[safe_hf_post] request error for {url}: {e}")
        raise

def convert_to_wav(input_path: str) -> str:
    """
    Convert input audio/video to WAV 16k mono using ffmpeg.
    Requires ffmpeg installed in environment.
    Returns path to .wav file (temp) or raises.
    """
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_path = out.name
    out.close()
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000", "-ac", "1",
        out_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"[convert_to_wav] ffmpeg failed: {e}")
        # fall back: return original file (whisper may accept it) or raise
        raise

# ---------- HUGGING FACE HELPERS ----------
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
GODEL_MODEL = "microsoft/GODEL-v1_1-large-seq2seq"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-small")

def detect_emotion(text: str) -> str:
    if not text:
        return "neutral"
    try:
        url = f"https://api-inference.huggingface.co/models/{EMOTION_MODEL}"
        res = safe_hf_post(url, headers=HEADERS, json={"inputs": text}, timeout=15)
        if isinstance(res, list) and res:
            data = res[0]
            # res[0] usually is list of {label, score}
            if isinstance(data, list):
                label = max(data, key=lambda x: x["score"])["label"].lower()
            elif isinstance(data, dict):
                # sometimes structure differs
                label = data.get("label", "neutral").lower()
            else:
                label = "neutral"
            if "sad" in label: return "sadness"
            if "fear" in label: return "fear"
            if "joy" in label: return "joy"
            if "anger" in label: return "anger"
        return "neutral"
    except Exception:
        return "neutral"

def generate_reflection(user_text: str) -> str:
    if not user_text:
        return random.choice([
            "💭 God understands even the words you can’t speak. You’re loved.",
            "Psalm 46:1 — 'God is our refuge and strength.'"
        ])
    try:
        url = f"https://api-inference.huggingface.co/models/{GODEL_MODEL}"
        prompt = (
            "Instruction: be an empathetic Christian friend who gives faith-based encouragement.\n"
            f"Input: {user_text}\n"
            "Output:"
        )
        payload = {"inputs": prompt, "options": {"max_new_tokens": 150}}
        res = safe_hf_post(url, headers=HEADERS, json=payload, timeout=45)
        # HF returns list or dict depending on model
        if isinstance(res, list) and res:
            text = res[0].get("generated_text", "")
        elif isinstance(res, dict):
            text = res.get("generated_text", "") or res.get("text", "")
        else:
            text = ""
        text = (text or "").strip()
        if not text:
            return random.choice([
                "💭 God understands even the words you can’t speak. You’re loved.",
                "Psalm 46:1 — 'God is our refuge and strength.'"
            ])
        return text
    except Exception:
        return random.choice([
            "💭 God understands even the words you can’t speak. You’re loved.",
            "Psalm 46:1 — 'God is our refuge and strength.'"
        ])

def speech_to_text(file_path: str) -> str:
    """
    Send audio bytes to Hugging Face Whisper model and return text.
    Converts input to WAV first for better compatibility.
    """
    try:
        # ensure file exists and non-zero
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return ""
    except Exception:
        return ""

    try:
        # Convert to WAV for consistency
        try:
            wav_path = convert_to_wav(file_path)
        except Exception:
            # if conversion fails, use original file
            wav_path = file_path

        with open(wav_path, "rb") as f:
            data = f.read()

        url = f"https://api-inference.huggingface.co/models/{WHISPER_MODEL}"
        res = safe_hf_post(url, headers=HEADERS, data=data, timeout=60)
        # Hugging Face whisper typically returns dict with 'text' key
        if isinstance(res, dict):
            return res.get("text") or res.get("transcription") or ""
        return ""
    except Exception as e:
        print(f"[speech_to_text] error: {e}")
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

    if user_id and not rate_limited(user_id, "message"):
        await update.message.reply_text("⚠️ You're sending messages too quickly. Please wait a moment.")
        return

    # quick commands
    if text.lower().strip() in ("/start", "start"):
        return await start(update, context)
    if text.lower().strip() in ("/verse", "verse"):
        # simple verse fallback
        verse = random.choice([
            "Psalm 46:1 — 'God is our refuge and strength.'",
            "Philippians 4:6 — 'Do not be anxious about anything...'",
            "Isaiah 41:10 — 'Fear not, for I am with you.'"
        ])
        await update.message.reply_text(verse)
        return

    # main flow
    emotion = detect_emotion(text)
    reflection = generate_reflection(text)
    combo = f"{reflection}\n\n{get_response(emotion)}"
    try:
        await update.message.reply_text(combo)
    except Exception as e:
        print(f"[handle_text] reply error: {e}")

async def handle_audio_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles voice (ogg), audio, and video_note cases.
    """
    user = update.effective_user
    user_id = user.id if user else None

    if user_id and not rate_limited(user_id, "audio"):
        await update.message.reply_text("⚠️ You're sending audio too quickly. Please wait a moment.")
        return

    file_obj = None
    # prefer voice -> video_note -> audio
    if update.message.voice:
        file_obj = await update.message.voice.get_file()
    elif update.message.video_note:
        file_obj = await update.message.video_note.get_file()
    elif update.message.audio:
        file_obj = await update.message.audio.get_file()
    else:
        await update.message.reply_text("🎧 Couldn't find audio in that message.")
        return

    # save to temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            await file_obj.download_to_drive(tmp.name)
            tmp_path = tmp.name
    except Exception as e:
        print(f"[handle_audio_like] download error: {e}")
        await update.message.reply_text("⚠️ Error downloading audio. Please try again.")
        return

    # transcribe
    try:
        transcript = speech_to_text(tmp_path)
    except Exception as e:
        print(f"[handle_audio_like] transcription error: {e}")
        transcript = ""

    # remove temp files, best-effort
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
    reply = f"{reflection}\n\n{get_response(emotion)}"
    try:
        await update.message.reply_text(reply)
    except Exception as e:
        print(f"[handle_audio_like] reply error: {e}")

# register handlers
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
# accept voice, audio, and video notes
tg_app.add_handler(MessageHandler(filters.VOICE | filters.VIDEO_NOTE | filters.AUDIO, handle_audio_like))

# ---------- MAIN ----------
if __name__ == "__main__":
    import uvicorn

    # Start FastAPI in a background thread (so UptimeRobot can ping)
    def start_api():
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info", reload=False)

    print("Starting FastAPI heartbeat thread...")
    threading.Thread(target=start_api, daemon=True).start()

    # Start telegram long polling in main thread (PTB handles async internally)
    print("✅ Telegram bot initialized, starting long polling...")
    tg_app.run_polling()
