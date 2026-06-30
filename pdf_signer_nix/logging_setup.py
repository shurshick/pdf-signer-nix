from __future__ import annotations

import logging

from .paths import log_dir


SECRET_WORDS = ("pin", "password", "passwd", "secret", "private key", "закрытый ключ")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        lower = message.lower()
        if any(word in lower for word in SECRET_WORDS):
            record.msg = "<redacted sensitive log message>"
            record.args = ()
        return True


def configure_logging() -> None:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(directory / "app.log", encoding="utf-8")
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
