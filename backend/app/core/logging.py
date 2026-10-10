import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Optional

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for CloudWatch, OpenTelemetry, and container stdout.
    Omits sensitive tokens and secrets.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "correlation_id": correlation_id_ctx.get(),
            "tenant_id": tenant_id_ctx.get(),
        }

        # Include exception trace if present
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        # Include custom extra attributes
        if hasattr(record, "extra_fields"):
            log_object.update(record.extra_fields)

        return json.dumps(log_object)


def setup_logging(log_level: str = "INFO"):
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Quiet external noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger("agentic_rag")
