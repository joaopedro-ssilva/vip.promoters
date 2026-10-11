"""Logging estruturado (JSON). Nunca registrar tokens, senhas, cookies ou query strings."""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings

_EXTRA = ("request_id", "method", "path", "status", "duration_ms", "event")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _EXTRA:
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
    # httpx registra a URL completa (pode conter tokens em query string)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # arq registra os ARGUMENTOS de cada job (conteudo de webhooks): so avisos e erros
    logging.getLogger("arq.worker").setLevel(logging.WARNING)
    logging.getLogger("arq.jobs").setLevel(logging.WARNING)
