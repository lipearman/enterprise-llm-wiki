"""
Logging configuration.

Development  (APP_ENV != "production"):
    Human-readable:  2025-01-01 12:00:00 INFO  enterprise_llm_wiki - message

Production   (APP_ENV == "production"):
    JSON one-liner per log entry — ready for log-aggregation tools
    (Datadog, Loki, CloudWatch, etc.)

    {"time": "2025-01-01T12:00:00Z", "level": "INFO",
     "logger": "enterprise_llm_wiki", "message": "..."}
"""

import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Emit one compact JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def _build_logger() -> logging.Logger:
    # Lazy import to avoid circular dependency at module load time
    from app.core.config import settings

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.APP_ENV == "production":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s - %(message)s")
        )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if this module is reloaded (uvicorn --reload)
    root.handlers.clear()
    root.addHandler(handler)

    log = logging.getLogger("enterprise_llm_wiki")
    log.setLevel(level)
    return log


logger = _build_logger()
