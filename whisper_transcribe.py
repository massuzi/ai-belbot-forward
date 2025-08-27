# whisper_transcribe.py
import requests

def transcribe_audio_from_url(url: str, language: str = "nl"):
    """
    Upload de audio-URL naar Whisper (of jouw backend) en retourneer tekst.
    language: ISO code, bv. "nl"
    """
    # Voorbeeld met OpenAI Whisper API:
    # (pas aan naar je eigen implementatie indien nodig)
    import openai
    from tempfile import NamedTemporaryFile

    # Download audio lokaal (Twilio geeft publieke RecordingUrl)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(r.content)
        tmp = f.name

    audio_file = open(tmp, "rb")
    transcript = openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language=language
        # eventueel prompt="Context: logistiek, forwarding, transport"
    )
    audio_file.close()
    return transcript.text.strip() if hasattr(transcript, "text") else ""
