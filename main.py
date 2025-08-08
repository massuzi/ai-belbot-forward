
from flask import Flask
from twilio_handler import twilio_voice_handler, twilio_recording_handler

app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    return twilio_voice_handler()

@app.route("/handle-recording", methods=["POST"])
def handle_recording():
    return twilio_recording_handler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
