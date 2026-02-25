import os
import requests
from dotenv import load_dotenv

load_dotenv()


class TelegramNotifier:
    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

    def send(self, message: str):
        if not self.enabled:
            return
        try:
            requests.post(
                self.BASE_URL.format(token=self.token),
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            print(f"⚠️  Telegram error: {e}")
