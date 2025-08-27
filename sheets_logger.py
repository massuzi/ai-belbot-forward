# sheets_logger.py
import os
from datetime import datetime

from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")  # <-- lange ID uit de Google Sheets URL
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_sheet = None


def _require_env(name: str, value: str):
    if not value:
        raise RuntimeError(
            f"{name} ontbreekt. Zet deze in je .env (bijv. {name}=...)"
        )


def _get_sheet():
    """Maak een gspread client en open sheet1 via de Sheet ID (lazy)."""
    global _client, _sheet

    if _sheet is not None:
        return _sheet

    _require_env("SHEET_ID", SHEET_ID)
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"GOOGLE_CREDENTIALS_FILE wijst naar '{CREDENTIALS_FILE}', maar dat bestand bestaat niet."
        )

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE, SCOPE
    )
    _client = gspread.authorize(creds)

    # Belangrijk: open via key/ID, niet via naam
    _sheet = _client.open_by_key(SHEET_ID).sheet1
    return _sheet


def log_to_sheet(answer1: str, answer2: str, answer3: str, email: str):
    """
    Voeg een rij toe:
    [timestamp, answer1, answer2, answer3, email]
    """
    sheet = _get_sheet()
    sheet.append_row(
        [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            answer1 or "",
            answer2 or "",
            answer3 or "",
            email or "",
        ]
    )
