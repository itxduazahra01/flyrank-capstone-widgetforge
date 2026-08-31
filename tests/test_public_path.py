import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import OutboxEvent, Submission, Widget, WidgetEvent
from app.db.session import Base, SessionLocal, engine
from app.integrations.geo import GeoResult
from app.integrations.notifier import WebhookNotifier
from app.main import app
from app.services.submission import analytics_limiter, limiter, accept_submission
from app.workers.outbox import process_pending_events
from scripts.seed_demo import seed


class WorkingGeo:
    name = "backup"
    def lookup(self, ip): return GeoResult(country="Pakistan", city="Karachi", provider=self.name)


class FailingGeo:
    name = "primary"
    def lookup(self, ip): raise RuntimeError("provider down")


class FailingNotifier:
    def send_submission_accepted(self, submission, event_id): raise RuntimeError("down")


class PublicPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("WIDGETFORGE_TEST_MODE") != "1" or "test" not in str(engine.url):
            raise RuntimeError("Refusing to reset a non-test database. Run with WIDGETFORGE_TEST_MODE=1 and a test DATABASE_URL.")
        Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine); seed()
        cls.client = TestClient(app)

    def setUp(self):
        limiter.requests.clear()
        analytics_limiter.requests.clear()
        with SessionLocal() as db:
            self.widget = db.scalar(select(Widget).where(Widget.widget_type == "signup"))

    def payload(self, key="00000000-0000-0000-0000-000000000010"):
        return {"widget_id": self.widget.public_id, "fields": {"email": "lead@example.com", "name": "Lead"}, "website": ""}, {"Origin": "http://localhost:8080", "Idempotency-Key": key}

    def test_config_cors_cache_and_submission_replay(self):
        config = self.client.get(f"/public/v1/widgets/{self.widget.public_id}/config", headers={"Origin": "http://localhost:8081"})
        self.assertEqual(config.status_code, 200); self.assertIn("max-age=300", config.headers["cache-control"])
        self.assertEqual(config.json()["display_options"]["primary_color"], "#2457E6")
        self.assertEqual(config.headers["access-control-allow-origin"], "http://localhost:8081")
        bundle = self.client.get("/widget.v1.js")
        self.assertEqual(bundle.status_code, 200)
        self.assertEqual(bundle.headers["cache-control"], "public, max-age=31536000, immutable")
        self.assertEqual(self.client.get(f"/public/v1/widgets/{self.widget.public_id}/config", headers={"If-None-Match": config.headers["etag"]}).status_code, 304)
        payload, headers = self.payload()
        first = self.client.post("/public/v1/submissions", json=payload, headers=headers)
        replay = self.client.post("/public/v1/submissions", json=payload, headers=headers)
        self.assertEqual(first.status_code, 201); self.assertFalse(first.json()["replayed"])
        self.assertEqual(replay.json()["id"], first.json()["id"]); self.assertTrue(replay.json()["replayed"])
        login = self.client.post("/api/v1/auth/login", json={"email": "alice@acme.test", "password": "DemoPass123!"})
        owner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        webhook = self.client.put(f"/api/v1/widgets/{self.widget.id}/webhook", json={"url": "https://hooks.example/acme", "is_active": True}, headers=owner_headers)
        self.assertEqual(webhook.status_code, 200); self.assertEqual(webhook.json()["widget_id"], self.widget.id)
        event = self.client.post("/public/v1/events", json={"widget_id": self.widget.public_id, "event_type": "widget_viewed", "session_id": "visitor-session-001"}, headers={"Origin": "http://localhost:8080"})
        self.assertEqual(event.status_code, 204)
        duplicate_event = self.client.post("/public/v1/events", json={"widget_id": self.widget.public_id, "event_type": "widget_viewed", "session_id": "visitor-session-001"}, headers={"Origin": "http://localhost:8080"})
        self.assertEqual(duplicate_event.status_code, 204)
        started = self.client.post("/public/v1/events", json={"widget_id": self.widget.public_id, "event_type": "form_started", "session_id": "visitor-session-001"}, headers={"Origin": "http://localhost:8080"})
        self.assertEqual(started.status_code, 204)
        summary = self.client.get("/api/v1/dashboard/summary", headers=owner_headers)
        self.assertEqual(summary.status_code, 200); self.assertGreaterEqual(summary.json()["widget_views"], 1); self.assertGreaterEqual(summary.json()["form_starts"], 1); self.assertGreaterEqual(summary.json()["accepted_submissions"], 1)
        analytics = self.client.get("/api/v1/dashboard/analytics?days=7", headers=owner_headers)
        self.assertEqual(analytics.status_code, 200); self.assertEqual(analytics.json()["days"], 7); self.assertGreaterEqual(analytics.json()["widget_views"], 1); self.assertIsInstance(analytics.json()["by_country"], list)
        deliveries = self.client.get("/api/v1/webhook-deliveries", headers=owner_headers)
        self.assertEqual(deliveries.status_code, 200); self.assertIn(first.json()["id"], [item["submission_id"] for item in deliveries.json()])
        with SessionLocal() as db:
            events = list(db.scalars(select(WidgetEvent)))
            self.assertEqual(sum(event.event_type == "widget_viewed" for event in events), 1)
            self.assertEqual(sum(event.event_type == "form_started" for event in events), 1)
        updated = self.client.patch(f"/api/v1/submissions/{first.json()['id']}/status", json={"lead_status": "contacted"}, headers=owner_headers)
        self.assertEqual(updated.status_code, 200); self.assertEqual(updated.json()["lead_status"], "contacted")
        bulk = self.client.patch("/api/v1/submissions/bulk-status", json={"submission_ids": [first.json()["id"]], "lead_status": "qualified"}, headers=owner_headers)
        self.assertEqual(bulk.status_code, 200); self.assertEqual(bulk.json()["updated"], 1)
        noted = self.client.patch(f"/api/v1/submissions/{first.json()['id']}/notes", json={"notes": "Follow up with the product team."}, headers=owner_headers)
        self.assertEqual(noted.status_code, 200); self.assertEqual(noted.json()["notes"], "Follow up with the product team.")
        filtered = self.client.get("/api/v1/submissions?lead_status=qualified", headers=owner_headers)
        self.assertEqual(filtered.status_code, 200); self.assertIn(first.json()["id"], [item["id"] for item in filtered.json()])
        with SessionLocal() as db:
            db.get(Submission, first.json()["id"]).geo_country = "Pakistan"
            db.commit()
        country_filtered = self.client.get("/api/v1/submissions?country=Pakistan", headers=owner_headers)
        self.assertEqual(country_filtered.status_code, 200); self.assertIn(first.json()["id"], [item["id"] for item in country_filtered.json()])
        page = self.client.get("/api/v1/submissions/page?limit=1", headers=owner_headers)
        self.assertEqual(page.status_code, 200); self.assertEqual(len(page.json()["items"]), 1); self.assertIn("next_cursor", page.json())
        self.assertEqual(self.client.get("/api/v1/submissions/page?cursor=not-a-cursor", headers=owner_headers).status_code, 422)
        exported = self.client.get("/api/v1/submissions/export?lead_status=qualified", headers=owner_headers)
        self.assertEqual(exported.status_code, 200); self.assertIn("text/csv", exported.headers["content-type"]); self.assertIn(first.json()["id"], exported.text)
        bob_login = self.client.post("/api/v1/auth/login", json={"email": "bob@beta.test", "password": "DemoPass123!"})
        bob_headers = {"Authorization": f"Bearer {bob_login.json()['access_token']}"}
        self.assertEqual(self.client.put(f"/api/v1/widgets/{self.widget.id}/webhook", json={"url": "https://hooks.example/beta", "is_active": True}, headers=bob_headers).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/submissions/{first.json()['id']}/status", json={"lead_status": "closed"}, headers=bob_headers).status_code, 404)
        self.assertEqual(self.client.patch("/api/v1/submissions/bulk-status", json={"submission_ids": [first.json()["id"]], "lead_status": "closed"}, headers=bob_headers).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/submissions/{first.json()['id']}/notes", json={"notes": "not allowed"}, headers=bob_headers).status_code, 404)
        self.assertNotIn(first.json()["id"], [item["submission_id"] for item in self.client.get("/api/v1/webhook-deliveries", headers=bob_headers).json()])
        self.assertEqual(self.client.get("/api/v1/dashboard/analytics", headers=bob_headers).json()["widget_views"], 0)

    def test_oversized_submission_returns_413(self):
        payload, headers = self.payload("00000000-0000-0000-0000-000000000050")
        payload["fields"]["name"] = "x" * 20_000
        response = self.client.post("/public/v1/submissions", json=payload, headers=headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "payload_too_large")

    def test_allowed_origin_restricts_public_submission(self):
        with SessionLocal() as db:
            self.widget.display_options = {"allowed_origins": ["https://acme.example"]}
            db.merge(self.widget); db.commit()
        allowed_config = self.client.get(f"/public/v1/widgets/{self.widget.public_id}/config", headers={"Origin": "https://acme.example"})
        self.assertEqual(allowed_config.status_code, 200)
        blocked_config = self.client.get(f"/public/v1/widgets/{self.widget.public_id}/config", headers={"Origin": "https://blocked.example"})
        self.assertEqual(blocked_config.status_code, 403)
        payload, headers = self.payload("00000000-0000-0000-0000-000000000060")
        headers["Origin"] = "https://acme.example"
        allowed = self.client.post("/public/v1/submissions", json=payload, headers=headers)
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.headers["access-control-allow-origin"], "https://acme.example")
        payload, headers = self.payload("00000000-0000-0000-0000-000000000061")
        headers["Origin"] = "https://blocked.example"
        blocked = self.client.post("/public/v1/submissions", json=payload, headers=headers)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.headers["access-control-allow-origin"], "https://blocked.example")
        with SessionLocal() as db:
            widget = db.get(Widget, self.widget.id)
            widget.display_options = {}
            db.commit()

    def test_preflight_and_both_geo_providers_down(self):
        preflight = self.client.options("/public/v1/submissions", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,idempotency-key"})
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight.headers["access-control-allow-origin"], "http://localhost:8081")
        with SessionLocal() as db:
            submission, _ = accept_submission(db, public_id=self.widget.public_id, fields={"email": "nogeo@example.com", "name": "No Geo"}, honeypot="", idempotency_key="00000000-0000-0000-0000-000000000040", ip="127.0.0.1", origin=None, geo_providers=[FailingGeo(), FailingGeo()])
            self.assertIsNone(submission.geo_country)
            self.assertIsNone(submission.geo_provider)

    def test_honeypot_validation_and_rate_limit(self):
        payload, headers = self.payload("00000000-0000-0000-0000-000000000020")
        payload["website"] = "bot"
        with SessionLocal() as db:
            before = len(list(db.scalars(select(Submission))))
        self.assertEqual(self.client.post("/public/v1/submissions", json=payload, headers=headers).status_code, 201)
        with SessionLocal() as db:
            self.assertEqual(len(list(db.scalars(select(Submission)))), before)
        limiter.requests.clear(); payload["website"] = ""; payload["fields"] = {"unknown": "x"}
        self.assertEqual(self.client.post("/public/v1/submissions", json=payload, headers=headers).status_code, 422)
        limiter.requests.clear(); payload["fields"] = {"email": "fresh@example.com", "name": "Fresh"}
        for index in range(5):
            headers["Idempotency-Key"] = f"00000000-0000-0000-0000-{index:012d}"
            self.assertEqual(self.client.post("/public/v1/submissions", json=payload, headers=headers).status_code, 201)
        headers["Idempotency-Key"] = "00000000-0000-0000-0000-999999999999"
        self.assertEqual(self.client.post("/public/v1/submissions", json=payload, headers=headers).status_code, 429)

    def test_geo_fallback_and_failed_notification_preserve_submission(self):
        with SessionLocal() as db:
            submission, replayed = accept_submission(db, public_id=self.widget.public_id, fields={"email": "geo@example.com", "name": "Geo"}, honeypot="", idempotency_key="00000000-0000-0000-0000-000000000030", ip="127.0.0.1", origin=None, geo_providers=[FailingGeo(), WorkingGeo()])
            self.assertFalse(replayed); self.assertEqual(submission.geo_provider, "backup")
            self.assertGreaterEqual(process_pending_events(db, FailingNotifier()), 1)
            event = db.scalar(select(OutboxEvent).where(OutboxEvent.submission_id == submission.id))
            self.assertEqual(event.status, "pending"); self.assertEqual(event.attempt_count, 1)

    def test_webhook_notifier_signs_a_delivery(self):
        with SessionLocal() as db:
            submission = db.scalar(select(Submission).where(Submission.tenant_id == self.widget.tenant_id))
            response = Mock(); response.raise_for_status.return_value = None
            with patch("app.integrations.notifier.httpx.post", return_value=response) as post:
                WebhookNotifier("https://hooks.example/lead", "test-secret", previous_secret="old-secret").send_submission_accepted(submission, "delivery-123")
            self.assertEqual(post.call_args.kwargs["headers"]["X-WidgetForge-Delivery"], "delivery-123")
            self.assertTrue(post.call_args.kwargs["headers"]["X-WidgetForge-Signature"].startswith("sha256="))
            self.assertTrue(post.call_args.kwargs["headers"]["X-WidgetForge-Signature-Previous"].startswith("sha256="))


if __name__ == "__main__": unittest.main()
