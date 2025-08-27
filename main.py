from flask import Flask, send_from_directory
from dotenv import load_dotenv
import os

from twilio_handler import twilio_voice_handler, twilio_recording_handler, twilio_gather_handler

# Laad .env variabelen
load_dotenv()

app = Flask(__name__)

# Map voor TTS-audio (staat ook in .env als je wilt)
AUDIO_DIR = os.getenv("AUDIO_DIR", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.route("/voice", methods=["POST"])
def voice():
    return twilio_voice_handler()

@app.route("/handle-recording", methods=["POST"])
def handle_recording():
    return twilio_recording_handler()

@app.route("/handle-gather", methods=["POST"])
def handle_gather():
    return twilio_gather_handler()

# Route om audio-bestanden te serveren
@app.route("/audio/<path:fname>")
def audio(fname):
    return send_from_directory(AUDIO_DIR, fname, mimetype="audio/mpeg")

if __name__ == "__main__":
    # Start server
    port = int(os.getenv("PORT", 5050))
    app.run(debug=True, host="0.0.0.0", port=port)
