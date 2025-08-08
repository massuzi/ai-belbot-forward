
from flask import request, Response
from twilio.twiml.voice_response import VoiceResponse
from whisper_transcribe import transcribe_audio_from_url
from gpt_logic import process_answer
from tts import generate_audio
from sheets_logger import log_to_sheet
import os
import requests

question_index = 0
questions = [
    "Doet u import, export of beide?",
    "Welke transportmodi gebruikt u het meest: zee, lucht of weg?",
    "Van en naar welke landen vervoert u voornamelijk?"
]
answers = []

def twilio_voice_handler():
    response = VoiceResponse()
    response.say("Welkom bij onze logistieke intake lijn.", language="nl-NL")
    response.say(questions[0], language="nl-NL")
    response.record(
        timeout=3,
        transcribe=False,
        maxLength=30,
        action="/handle-recording",
        method="POST",
        playBeep=True
    )
    return Response(str(response), mimetype="text/xml")

def twilio_recording_handler():
    global question_index, answers
    recording_url = request.form.get("RecordingUrl")
    audio_url = f"{recording_url}.mp3"
    transcript = transcribe_audio_from_url(audio_url)

    answers.append(transcript)

    question_index += 1

    response = VoiceResponse()

    if question_index < len(questions):
        next_question = questions[question_index]
        response.say(f"Bedankt. {next_question}", language="nl-NL")
        response.record(
            timeout=3,
            transcribe=False,
            maxLength=30,
            action="/handle-recording",
            method="POST",
            playBeep=True
        )
    else:
        response.say("Bedankt voor uw antwoorden. Wij nemen zo snel mogelijk contact met u op.", language="nl-NL")
        log_to_sheet(*answers, email="n.v.t.")
        question_index = 0
        answers = []

    return Response(str(response), mimetype="text/xml")
