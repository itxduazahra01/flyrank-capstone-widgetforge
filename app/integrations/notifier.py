import hashlib
import hmac
import json

import httpx

from app.db.models import Submission


class Notifier:
    def send_submission_accepted(self, submission: Submission, event_id: str) -> None:
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    def send_submission_accepted(self, submission: Submission, event_id: str) -> None:
        # No PII is logged; an event ID lets any future receiver deduplicate.
        print(f"notification event={event_id} submission={submission.id}")


class WebhookNotifier(Notifier):
    """POST signed delivery payloads from the outbox worker only."""

    def __init__(self, url: str, secret: str, timeout_seconds: float = 5.0, previous_secret: str = ""):
        if not url or not secret:
            raise ValueError("WEBHOOK_URL and WEBHOOK_SECRET are required for webhook notifications")
        self.url = url
        self.secret = secret.encode()
        self.previous_secret = previous_secret.encode() if previous_secret else None
        self.timeout_seconds = timeout_seconds

    def send_submission_accepted(self, submission: Submission, event_id: str) -> None:
        payload = {
            "event": "submission.accepted",
            "delivery_id": event_id,
            "data": {
                "submission_id": submission.id,
                "tenant_id": submission.tenant_id,
                "widget_id": submission.widget_id,
                "submitted_at": submission.created_at.isoformat(),
                "fields": submission.payload,
                "source_origin": submission.source_origin,
            },
        }
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-WidgetForge-Event": "submission.accepted",
            "X-WidgetForge-Delivery": event_id,
            "X-WidgetForge-Signature": f"sha256={signature}",
        }
        if self.previous_secret:
            previous_signature = hmac.new(self.previous_secret, body, hashlib.sha256).hexdigest()
            headers["X-WidgetForge-Signature-Previous"] = f"sha256={previous_signature}"
        response = httpx.post(
            self.url,
            content=body,
            timeout=self.timeout_seconds,
            headers=headers,
        )
        response.raise_for_status()
