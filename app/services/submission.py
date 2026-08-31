import hashlib
import hmac
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import OutboxEvent, Submission, Widget, WidgetEvent
from app.integrations.geo import GeoProvider, configured_geo_providers, resolve_geo


class InMemoryRateLimiter:
    def __init__(self):
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        settings = get_settings()
        now = time.monotonic()
        window = self.requests[key]
        while window and window[0] <= now - settings.rate_limit_window_seconds:
            window.popleft()
        if len(window) >= settings.rate_limit_max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests", headers={"Retry-After": str(settings.rate_limit_window_seconds)})
        window.append(now)


limiter = InMemoryRateLimiter()
analytics_limiter = InMemoryRateLimiter()


def hash_ip(ip: str) -> str:
    return hmac.new(get_settings().ip_hash_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def get_active_widget(db: Session, public_id: str) -> Widget:
    widget = db.scalar(select(Widget).where(Widget.public_id == public_id, Widget.is_active.is_(True)))
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


def validate_fields(widget: Widget, fields: dict) -> dict:
    schema = {item["name"]: item for item in widget.form_fields}
    unknown = set(fields) - set(schema)
    if unknown:
        raise HTTPException(status_code=422, detail="Unknown form field")
    cleaned = {}
    for name, definition in schema.items():
        value = fields.get(name)
        if definition.get("required") and (value is None or not str(value).strip()):
            raise HTTPException(status_code=422, detail=f"{name} is required")
        if value is None:
            continue
        if not isinstance(value, str) or len(value) > definition.get("max_length", 254):
            raise HTTPException(status_code=422, detail=f"{name} is invalid")
        if definition.get("type") == "email" and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise HTTPException(status_code=422, detail=f"{name} is invalid")
        cleaned[name] = value.strip()
    return cleaned


def accept_submission(db: Session, *, public_id: str, fields: dict, honeypot: str, idempotency_key: str, ip: str, origin: str | None, geo_providers: list[GeoProvider] | None = None):
    widget = get_active_widget(db, public_id)
    limiter.check(f"{hash_ip(ip)}:{widget.public_id}")
    if honeypot:
        return None, False
    existing = db.scalar(select(Submission).where(Submission.widget_id == widget.id, Submission.idempotency_key == idempotency_key))
    if existing:
        return existing, True
    payload = validate_fields(widget, fields)
    geo = resolve_geo(ip, geo_providers if geo_providers is not None else configured_geo_providers())
    submission = Submission(tenant_id=widget.tenant_id, widget_id=widget.id, idempotency_key=idempotency_key, payload=payload, source_origin=origin, ip_hash=hash_ip(ip), geo_country=geo.country if geo else None, geo_city=geo.city if geo else None, geo_provider=geo.provider if geo else None)
    db.add(submission)
    db.flush()
    db.add(WidgetEvent(tenant_id=widget.tenant_id, widget_id=widget.id, event_type="submission_accepted", source_origin=origin, session_hash=hash_ip(f"submission:{idempotency_key}")))
    db.add(OutboxEvent(submission_id=submission.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Submission).where(Submission.widget_id == widget.id, Submission.idempotency_key == idempotency_key))
        if existing:
            return existing, True
        raise
    db.refresh(submission)
    return submission, False
