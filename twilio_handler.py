# twilio_handler.py
from flask import request, Response, url_for
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
import os
import logging

from whisper_transcribe import transcribe_audio_from_url  # fallback only
from tts import generate_audio
from sheets_logger import log_to_sheet

load_dotenv()
logger = logging.getLogger(__name__)

QUESTIONS = [
    "Doet u import, export of beide?",
    "Welke transportmodi gebruikt u het meest: zee, lucht of weg?",
    "Van en naar welke landen vervoert u voornamelijk?"
]

state = {}  # CallSid -> {"index": int, "answers": [str, ...]}

def _ensure_state(call_sid: str):
    if call_sid not in state:
        state[call_sid] = {"index": 0, "answers": []}
    return state[call_sid]

def _say_or_play(resp: VoiceResponse, text: str):
    """TTS via ElevenLabs; fallback naar <Say>."""
    try:
        mp3_path = generate_audio(text)
        public_url = request.url_root.strip("/") + url_for("audio", fname=os.path.basename(mp3_path))
        resp.play(public_url)
    except Exception:
        logger.exception("TTS failed; falling back to <Say>")
        resp.say(text, language="nl-NL")

def _gather_block(resp: VoiceResponse):
    """Twilio ASR (aanbevolen)."""
    resp.gather(
        input="speech",
        language="nl-NL",
        speech_timeout="auto",
        # help Twilio met domeintermen
        hints="import, export, zeevracht, luchtvracht, wegtransport, container, douane",
        action="/handle-gather",
        method="POST"
    )

def _record_block(resp: VoiceResponse):
    """Fallback: neem op en transcribeer met Whisper."""
    resp.record(
        timeout=6,
        maxLength=45,
        transcribe=False,
        recording_format="wav",   # belangrijk voor betere STT
        playBeep=True,
        action="/handle-recording",
        method="POST"
    )

def twilio_voice_handler():
    """Start: welkom + vraag + Gather (speech)."""
    call_sid = request.form.get("CallSid", "unknown")
    st = _ensure_state(call_sid)

    resp = VoiceResponse()
    _say_or_play(resp, "Welkom bij onze logistieke intake lijn. Spreek na de toon.")
    _say_or_play(resp, QUESTIONS[st["index"]])

    # EERST Gather (Twilio ASR)
    _gather_block(resp)
    return Response(str(resp), mimetype="text/xml")

def twilio_gather_handler():
    """Verwerkt Twilio's SpeechResult. Fallback naar record als leeg."""
    call_sid = request.form.get("CallSid", "unknown")
    st = _ensure_state(call_sid)
    resp = VoiceResponse()

    speech = (request.form.get("SpeechResult") or "").strip()
    logger.info("Gather SpeechResult", extra={"call_sid": call_sid, "text": speech})

    if not speech:
        # Niets verstaan? Fallback naar record+Whisper
        _say_or_play(resp, "Ik heb geen antwoord gehoord. Kunt u het nog eens herhalen na de toon?")
        _record_block(resp)
        return Response(str(resp), mimetype="text/xml")

    # Oké, we hebben tekst
    st["answers"].append(speech)
    st["index"] += 1

    if st["index"] < len(QUESTIONS):
        _say_or_play(resp, "Bedankt.")
        _say_or_play(resp, QUESTIONS[st["index"]])
        _gather_block(resp)  # volgende vraag weer via Gather
        return Response(str(resp), mimetype="text/xml")

    # Klaar -> loggen
    try:
        a1, a2, a3 = (st["answers"] + ["", "", ""])[:3]
        log_to_sheet(a1, a2, a3, email="n.v.t.")
    except Exception:
        logger.exception("Sheets logging failed", extra={"call_sid": call_sid})

    _say_or_play(resp, "Bedankt voor uw antwoorden. Wij nemen zo snel mogelijk contact met u op.")
    state.pop(call_sid, None)
    return Response(str(resp), mimetype="text/xml")

def twilio_recording_handler():
    """Fallback route (zoals je al had) — Whisper op de opname."""
    call_sid = request.form.get("CallSid", "unknown")
    st = _ensure_state(call_sid)
    resp = VoiceResponse()

    recording_url = request.form.get("RecordingUrl")
    if not recording_url:
        _say_or_play(resp, "Ik heb niets ontvangen. Kunt u dat nog eens herhalen?")
        _record_block(resp)
        return Response(str(resp), mimetype="text/xml")

    transcript = ""
    try:
        transcript = transcribe_audio_from_url(f"{recording_url}.wav", language="nl")
    except Exception as e:
        logger.warning(f"Whisper .wav faalde: {e}, probeer .mp3")
        try:
            transcript = transcribe_audio_from_url(f'{recording_url}.mp3', language="nl")
        except Exception:
            logger.exception("Transcription failed (mp3 & wav)")

    transcript = (transcript or "").strip()
    logger.info("Whisper transcript", extra={"call_sid": call_sid, "text": transcript})

    if len(transcript.split()) < 1:
        _say_or_play(resp, "Sorry, ik verstond het niet helemaal. Kunt u dat nog eens herhalen?")
        _record_block(resp)
        return Response(str(resp), mimetype="text/xml")

    st["answers"].append(transcript)
    st["index"] += 1

    if st["index"] < len(QUESTIONS):
        _say_or_play(resp, "Bedankt.")
        _say_or_play(resp, QUESTIONS[st["index"]])
        _gather_block(resp)  # terug naar Gather voor de volgende vraag
        return Response(str(resp), mimetype="text/xml")

    try:
        a1, a2, a3 = (st["answers"] + ["", "", ""])[:3]
        log_to_sheet(a1, a2, a3, email="n.v.t.")
    except Exception:
        logger.exception("Sheets logging failed", extra={"call_sid": call_sid})

    _say_or_play(resp, "Bedankt voor uw antwoorden. Wij nemen zo snel mogelijk contact met u op.")
    state.pop(call_sid, None)
    return Response(str(resp), mimetype="text/xml")
