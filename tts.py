# tts.py
import os
import hashlib
from typing import Optional
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter, Retry

load_dotenv()

# ── Config uit .env ────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

AUDIO_DIR = os.getenv("AUDIO_DIR", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# ── HTTP sessie met retries/backoff ───────────────────────────────────────────
_session = requests.Session()
_retries = Retry(
    total=3,
    backoff_factor=0.6,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST", "GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.mount("http://", HTTPAdapter(max_retries=_retries))

# ── Helpers ───────────────────────────────────────────────────────────────────
def _require_env(var_name: str, value: str):
    if not value:
        raise RuntimeError(f"Missing environment variable: {var_name}")

def _hash_text(text: str, voice_id: str, model_id: str) -> str:
    h = hashlib.sha256()
    h.update((voice_id + "|" + model_id + "|" + text).encode("utf-8"))
    return h.hexdigest()[:16]

def _sanitize_filename(name: str) -> str:
    safe = "".join(c for c in (name or "") if c.isalnum() or c in ("-", "_", "."))
    return safe or "audio.mp3"

# ── Public API ────────────────────────────────────────────────────────────────
def generate_audio(
    text: str,
    filename: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    stability: float = 0.6,
    similarity_boost: float = 0.8,
) -> str:
    """
    Genereer een MP3 via ElevenLabs en sla op in AUDIO_DIR.
    - Caching op basis van (text + voice_id + model_id).
    - Retourneert het absolute pad naar het MP3-bestand.
    """
    # Sanity check
    text = (text or "").strip()
    if not text:
        raise ValueError("generate_audio: empty text")

    # Vereiste env vars
    _require_env("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
    voice_id = voice_id or ELEVENLABS_DEFAULT_VOICE_ID
    _require_env("ELEVENLABS_VOICE_ID", voice_id)
    model_id = model_id or ELEVENLABS_MODEL_ID

    # Caching-bestandsnaam
    base = _hash_text(text, voice_id, model_id)
    target_name = _sanitize_filename(filename) if filename else f"resp_{base}.mp3"
    out_path = os.path.join(AUDIO_DIR, target_name)

    # Cache-hit
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path

    # API call
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "belbot/1.0 (+ngrok)",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": stability, "similarity_boost": similarity_boost, "use_speaker_boost": True},
    }

    try:
        resp = _session.post(url, headers=headers, json=payload, timeout=(5, 60), stream=True)
        # Specifieke hints
        if resp.status_code == 401:
            raise RuntimeError("ElevenLabs: unauthorized (check ELEVENLABS_API_KEY).")
        if resp.status_code == 429:
            raise RuntimeError("ElevenLabs: rate limited (plan/credits/backoff).")
        resp.raise_for_status()
    except requests.RequestException as e:
        # Laat de bovenliggende laag beslissen wat te doen
        raise RuntimeError(f"ElevenLabs request failed: {e}") from e

    # Veilig schrijven met .part + atomic replace
    tmp_path = out_path + ".part"
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                f.write(chunk)
    os.replace(tmp_path, out_path)

    return out_path

def cleanup_audio_cache(max_files: int = 200) -> int:
    """
    Houd de audio-map opgeruimd: behoud de nieuwste `max_files`, verwijder de rest.
    Retourneert het aantal verwijderde bestanden.
    """
    mp3s = [
        os.path.join(AUDIO_DIR, f)
        for f in os.listdir(AUDIO_DIR)
        if f.lower().endswith(".mp3")
    ]
    mp3s.sort(key=os.path.getmtime, reverse=True)
    removed = 0
    for old in mp3s[max_files:]:
        try:
            os.remove(old)
            removed += 1
        except OSError:
            pass
    return removed
