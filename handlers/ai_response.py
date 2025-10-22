# handlers/ai_response.py
import os
import requests
import random
from utils.helpers import safe_request, truncate_text

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

# model selection: prefer a small instruct model (flan-t5-small/base)
HF_MODEL = os.getenv("HF_MODEL", "google/flan-t5-small")
HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def detect_emotion(text: str) -> str:
    """
    Simple wrapper for emotion detection using a Hugging Face model.
    For now: call a public emotion model or fallback to neutral.
    """
    try:
        # using j-hartmann/emotion-english-distilroberta-base
        url = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
        res = safe_request("post", url, headers=HF_HEADERS, json={"inputs": text}, timeout=15)
        if isinstance(res, list) and res:
            data = res[0]
            label = max(data, key=lambda x: x["score"])["label"].lower()
            if "sad" in label: return "sadness"
            if "fear" in label: return "fear"
            if "joy" in label: return "joy"
            if "anger" in label: return "anger"
        return "neutral"
    except Exception:
        return "neutral"

def generate_reflection(user_text: str) -> str:
    """
    Send a prompt to HF instruction model and return a short empathetic reflection.
    Keep prompt conservative and avoid long outputs (cost control).
    """
    prompt = (
        "Instruction: you are an empathetic Christian friend. Provide a short encouraging reflection "
        "that references faith and hope. Keep it to 1-3 short sentences.\n"
        f"Input: {truncate_text(user_text, 800)}\n"
        "Output:"
    )
    try:
        payload = {"inputs": prompt, "options": {"max_new_tokens": 120}}
        res = safe_request("post", HF_INFERENCE_URL, headers=HF_HEADERS, json=payload, timeout=30)
        if isinstance(res, list) and res:
            return res[0].get("generated_text", "").strip()
        if isinstance(res, dict):
            return res.get("generated_text", "").strip() or random.choice([
                "💭 God understands even the words you can’t speak. You’re loved.",
                "Psalm 46:1 — 'God is our refuge and strength.'"
            ])
        return random.choice([
            "💭 God understands even the words you can’t speak. You’re loved.",
            "Psalm 46:1 — 'God is our refuge and strength.'"
        ])
    except Exception:
        return random.choice([
            "💭 God understands even the words you can’t speak. You’re loved.",
            "Psalm 46:1 — 'God is our refuge and strength.'"
        ])
