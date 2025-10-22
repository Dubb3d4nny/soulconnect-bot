# handlers/voice_handler.py
import os
import tempfile
import subprocess
from utils.helpers import safe_request

# We'll use Hugging Face Whisper endpoint for STT. Model choice default: openai/whisper-small
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-small")
WHISPER_URL = f"https://api-inference.huggingface.co/models/{WHISPER_MODEL}"
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

def convert_to_wav(input_path: str) -> str:
    """Use ffmpeg to convert input (ogg, mp4 audio) to WAV for consistency."""
    base = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_path = base.name
    base.close()
    # Use ffmpeg via subprocess (ffmpeg must be available in environment)
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000", "-ac", "1", out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

def transcribe_audio_from_file(file_path: str) -> str:
    """
    Convert to WAV if needed and send bytes to WHISPER model.
    Returns transcript text or empty string.
    """
    # check file size
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return ""
    except Exception:
        return ""

    wav_path = convert_to_wav(file_path)

    with open(wav_path, "rb") as f:
        data = f.read()

    try:
        res = safe_request("post", WHISPER_URL, headers=HF_HEADERS, data=data, timeout=60)
        # HF sometimes returns dict with 'text' key
        if isinstance(res, dict):
            # try multiple keys
            return res.get("text") or res.get("transcription") or ""
        # some endpoints return a list
        return ""
    except Exception:
        return ""
