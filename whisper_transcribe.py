
import openai
import os
import requests

openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio_from_url(audio_url):
    audio_data = requests.get(audio_url).content
    with open("temp.mp3", "wb") as f:
        f.write(audio_data)
    audio_file = open("temp.mp3", "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]
