import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramNotifier:
    _BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            logger.debug("TelegramNotifier deshabilitado (sin token/chat_id)")

    def _post(self, method: str, payload: dict) -> bool:
        try:
            url = self._BASE.format(token=self.token, method=method)
            data = requests.post(url, json=payload, timeout=10).json()
            if data.get("ok"):
                return True
            logger.warning("Telegram rechazó '%s': %s", method, data.get("description"))
        except Exception as e:
            logger.error("Telegram error en '%s': %s", method, e)
        return False

    def send(self, message: str) -> None:
        if not self.enabled:
            return
        ok = self._post("sendMessage", {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        })
        if ok:
            logger.debug("Telegram: mensaje enviado")

    def send_photo(self, photo_url: str) -> None:
        """Envía una imagen a partir de una URL pública."""
        if not self.enabled:
            return
        ok = self._post("sendPhoto", {
            "chat_id": self.chat_id,
            "photo": photo_url,
        })
        if ok:
            logger.debug("Telegram: foto enviada (%s)", photo_url)

    def send_photo_bytes(self, image_bytes: bytes, filename: str = "card.png") -> None:
        """Envía una imagen generada en memoria (bytes)."""
        if not self.enabled:
            return
        try:
            url = self._BASE.format(token=self.token, method="sendPhoto")
            data = requests.post(
                url,
                data={"chat_id": self.chat_id},
                files={"photo": (filename, image_bytes, "image/png")},
                timeout=20,
            ).json()
            if data.get("ok"):
                logger.debug("Telegram: card enviada")
            else:
                logger.warning("Telegram rechazó card: %s", data.get("description"))
        except Exception as e:
            logger.error("Telegram error enviando card: %s", e)
