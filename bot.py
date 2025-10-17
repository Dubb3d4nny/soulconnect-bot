import os, random, requests, tempfile, asyncio, time
from flask import Flask, request
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

# ---------- FLASK ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "🕊️ SoulConnect running."

@app.route("/heartbeat")
def heartbeat():
    return "💓 alive"

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
            text = data[0].get("generated_text", "")
        else:
            text = data.get("generated_text", "")
        return text.strip()
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
        data = r.json()
        return data.get("text", "")
    except Exception:
        return ""

# ---------- TELEGRAM HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕊️ Welcome to SoulConnect — a safe place for your soul.\n"
        "Tell me what’s on your heart today."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    emotion = detect_emotion(user_text)
    reflection = generate_reflection(user_text)
    combo = f"{reflection}\n\n{get_response(emotion)}"
    await update.message.reply_text(combo)

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
    reply = f"{reflection}\n\n{get_response(emotion)}"
    await update.message.reply_text(reply)

# ---------- RUN ----------
async def run():
    port = int(os.getenv("PORT", 10000))
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    @app.post(f"/{BOT_TOKEN}")
    async def telegram_webhook():
        update = Update.de_json(request.get_json(force=True), tg_app.bot)
        await tg_app.process_update(update)
        return "ok", 200

    # Wait for Render to expose the public URL
    app_url = None
    for i in range(15):
        raw = os.getenv("RENDER_EXTERNAL_URL")
        if raw and raw.startswith("https://"):
            app_url = raw.rstrip("/")
            break
        print("⏳ Waiting for Render public URL...")
        time.sleep(2)

    if not app_url:
        app_url = "https://soulconnect.onrender.com"  # fallback
    webhook_url = f"{app_url}/{BOT_TOKEN}"
    print(f"📡 Using webhook URL: {webhook_url}")

    # Verify the URL before setting it
    try:
        r = requests.get(app_url, timeout=5)
        print(f"🌐 Webhook domain check: {r.status_code}")
    except Exception as e:
        print("⚠️ Could not verify domain:", e)

    # Retry setting webhook
    for attempt in range(3):
        try:
            ok = await tg_app.bot.set_webhook(url=webhook_url)
            if ok:
                print("✅ Webhook successfully set.")
                break
        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            await asyncio.sleep(3)

    app.run(host="0.0.0.0", port=port)

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
