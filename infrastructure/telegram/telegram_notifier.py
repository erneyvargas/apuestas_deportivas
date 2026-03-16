import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramNotifier:
    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            logger.debug("TelegramNotifier deshabilitado (sin token/chat_id)")

    def send(self, message: str):
        if not self.enabled:
            return
        try:
            response = requests.post(
                self.BASE_URL.format(token=self.token),
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            data = response.json()
            if data.get("ok"):
                logger.info("Telegram: mensaje enviado correctamente")
            else:
                logger.warning("Telegram rechazó el mensaje: %s", data.get("description"))
        except Exception as e:
            logger.error("Telegram error: %s", e)
