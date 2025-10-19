import os
import random
import requests
import tempfile
import asyncio
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
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# ---------- FASTAPI ----------
app = FastAPI()

@app.get("/")
def home():
    return {"message": "🕊️ SoulConnect running."}

@app.get("/heartbeat")
def heartbeat():
    return {"status": "💓 alive"}

# ---------- HUGGING FACE HELPERS ----------
def detect_emotion(text: str) -> str:
    url = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    try:
        res = requests.post(url, headers=HEADERS, json={"inputs": text}, timeout=20)
        data = res.json()[0]
        label = max(data, key=lambda x: x["score"])["label"].lower()
        if "sad" in label: return "sadness"
        if "fear" in label: return "fear"
        if "joy" in label: return "joy"
        if "anger" in label: return "neutral"
        return "neutral"
    except Exception:
        return "neutral"

def generate_reflection(user_text: str) -> str:
    url = "https://api-inference.huggingface.co/models/microsoft/GODEL-v1_1-large-seq2seq"
    prompt = (
        "Instruction: be an empathetic Christian friend who gives faith-based encouragement.\n"
        f"Input: {user_text}\n"
        "Output:"
    )
    try:
        r = requests.post(url, headers=HEADERS, json={"inputs": prompt}, timeout=45)
        data = r.json()
        if isinstance(data, list):
            return data[0].get("generated_text", "").strip()
        return data.get("generated_text", "").strip()
    except Exception:
        return random.choice([
            "💭 God understands even the words you can’t speak. You’re loved.",
            "Psalm 46:1 — 'God is our refuge and strength.'"
        ])

def speech_to_text(file_path: str) -> str:
    url = "https://api-inference.huggingface.co/models/openai/whisper-tiny"
    with open(file_path, "rb") as f:
        payload = f.read()
    try:
        r = requests.post(url, headers=HEADERS, data=payload, timeout=60)
        return r.json().get("text", "")
    except Exception:
        return ""

# ---------- TELEGRAM BOT ----------
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕊️ Welcome to SoulConnect — a safe place for your soul.\n"
        "Tell me what’s on your heart today."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    emotion = detect_emotion(user_text)
    reflection = generate_reflection(user_text)
    await update.message.reply_text(f"{reflection}\n\n{get_response(emotion)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        await file.download_to_drive(tmp.name)
        text = speech_to_text(tmp.name)
    if not text:
        await update.message.reply_text("🎧 Couldn't hear clearly, please try again.")
        return
    emotion = detect_emotion(text)
    reflection = generate_reflection(text)
    await update.message.reply_text(f"{reflection}\n\n{get_response(emotion)}")

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))

# ---------- LONG POLLING IN BACKGROUND ----------
async def run_bot():
    print("✅ Telegram bot initialized, starting long polling...")
    await tg_app.run_polling()

@app.on_event("startup")
async def startup_event():
    # Start Telegram bot in background
    asyncio.create_task(run_bot())
