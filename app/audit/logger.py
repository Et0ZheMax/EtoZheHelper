import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_event(db: Session, event_type: str, details: dict[str, Any] | None = None) -> None:
    """Persist an audit event without breaking the caller on audit failures."""
    try:
        event = AuditEvent(event_type=event_type, details=json.dumps(details or {}, ensure_ascii=False))
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
