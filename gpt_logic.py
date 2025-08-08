
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def process_answer(transcript):
    messages = [
        {"role": "system", "content": "Je bent een logistieke intake assistent."},
        {"role": "user", "content": transcript}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    return response['choices'][0]['message']['content']
