"""
ARGUS Structured Logging

Every important operation should log: timestamp, request_id, incident_id,
agent, action, duration, status, error — as structured JSON so it can be
piped into any log aggregator later.
"""
import logging
import sys
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any extra structured fields passed via `extra={...}`
        for key in ("request_id", "incident_id", "agent", "action", "duration", "status"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def log_structured_event(
    logger: logging.Logger,
    message: str,
    agent: str,
    action: str,
    status: str = "success",
    incident_id: str = None,
    duration: float = None,
    request_id: str = None,
    level: int = logging.INFO,
    **kwargs,
) -> None:
    """
    Standardized structured logging helper per Section 25.
    """
    extra = {
        "agent": agent,
        "action": action,
        "status": status,
    }
    if incident_id:
        extra["incident_id"] = incident_id
    if duration is not None:
        extra["duration"] = round(duration, 4)
    if request_id:
        extra["request_id"] = request_id
    extra.update(kwargs)

    logger.log(level, message, extra=extra)

