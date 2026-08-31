from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OutboxEvent, Submission, WidgetWebhook
from app.core.config import get_settings
from app.integrations.notifier import ConsoleNotifier, Notifier, WebhookNotifier

MAX_ATTEMPTS = 3
logger = logging.getLogger(__name__)


def process_pending_events(db: Session, notifier: Notifier | None = None) -> int:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    events = list(db.scalars(select(OutboxEvent).where(OutboxEvent.status == "pending", OutboxEvent.available_at <= now)))
    processed = 0
    for event in events:
        submission = db.get(Submission, event.submission_id)
        try:
            if submission is None:
                raise RuntimeError("Submission no longer exists")
            delivery_notifier = notifier
            if delivery_notifier is None and settings.notifier_mode == "webhook":
                endpoint = db.scalar(select(WidgetWebhook).where(WidgetWebhook.widget_id == submission.widget_id, WidgetWebhook.tenant_id == submission.tenant_id, WidgetWebhook.is_active.is_(True)))
                url = endpoint.url if endpoint else settings.webhook_url
                delivery_notifier = WebhookNotifier(url, settings.webhook_secret, settings.webhook_timeout_seconds, settings.webhook_previous_secret)
            delivery_notifier = delivery_notifier or ConsoleNotifier()
            delivery_notifier.send_submission_accepted(submission, event.id)
            event.status = "sent"
            event.attempt_count += 1
            event.last_error = None
        except Exception:
            event.attempt_count += 1
            event.last_error = "Notification delivery failed"
            if event.attempt_count >= MAX_ATTEMPTS:
                event.status = "failed"
                logger.error("Outbox event %s permanently failed after %s attempts", event.id, event.attempt_count)
            else:
                event.available_at = now + timedelta(seconds=2 ** event.attempt_count)
        processed += 1
    db.commit()
    return processed
