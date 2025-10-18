import os, random, requests, tempfile, asyncio
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
url = "[https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base](https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base)"
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
url = "[https://api-inference.huggingface.co/models/microsoft/GODEL-v1_1-large-seq2seq](https://api-inference.huggingface.co/models/microsoft/GODEL-v1_1-large-seq2seq)"
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
url = "[https://api-inference.huggingface.co/models/openai/whisper-tiny](https://api-inference.huggingface.co/models/openai/whisper-tiny)"
with open(file_path, "rb") as f:
payload = f.read()
try:
r = requests.post(url, headers=HEADERS, data=payload, timeout=60)
data = r.json()
return data.get("text", "")
except Exception:
return ""

# ---------- TELEGRAM ----------

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

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))

# ---------- TELEGRAM WEBHOOK ----------

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook():
try:
data = request.get_json(force=True)
update = Update.de_json(data, tg_app.bot)
await tg_app.process_update(update)
return "ok", 200
except Exception as e:
print("⚠️ Webhook processing error:", e)
return "error", 500

# ---------- MAIN ----------

def main():
port = int(os.getenv("PORT", 10000))
app_url = os.getenv("RENDER_EXTERNAL_URL", "[https://soulconnect.onrender.com").rstrip("/](https://soulconnect.onrender.com%22%29.rstrip%28%22/)")
webhook_url = f"{app_url}/{BOT_TOKEN}"

```
async def setup_webhook():
    await tg_app.bot.delete_webhook(drop_pending_updates=True)
    await tg_app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

asyncio.run(setup_webhook())

print(f"🌍 Running Flask on port {port}")
app.run(host="0.0.0.0", port=port)
```

if **name** == "**main**":
main()
