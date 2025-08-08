
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime

SHEET_NAME = "belbot_leads"
CREDENTIALS_FILE = "credentials.json"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

def log_to_sheet(answer1, answer2, answer3, email):
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        answer1,
        answer2,
        answer3,
        email
    ])
