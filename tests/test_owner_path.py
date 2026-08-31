import os
import unittest

from fastapi.testclient import TestClient

from app.db.session import Base, engine
from app.main import app
from scripts.seed_demo import seed


class OwnerPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("WIDGETFORGE_TEST_MODE") != "1" or "test" not in str(engine.url):
            raise RuntimeError("Refusing to reset a non-test database. Run with WIDGETFORGE_TEST_MODE=1 and a test DATABASE_URL.")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        seed()
        cls.client = TestClient(app)

    def login(self, email: str) -> dict[str, str]:
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": "DemoPass123!"})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_owner_crud_embed_and_tenant_isolation(self):
        alice_headers = self.login("alice@acme.test")
        bob_headers = self.login("bob@beta.test")

        create = self.client.post(
            "/api/v1/widgets",
            headers=alice_headers,
            json={
                "widget_type": "contact",
                "title": "Talk to Acme",
                "form_fields": [{"name": "email", "label": "Email", "type": "email", "required": True}],
                "button_text": "Send",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        widget = create.json()

        self.assertEqual(self.client.get("/api/v1/widgets", headers=alice_headers).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/widgets/{widget['id']}", headers=bob_headers).status_code, 404)
        self.assertEqual(
            self.client.patch(f"/api/v1/widgets/{widget['id']}", headers=bob_headers, json={"title": "Nope"}).status_code,
            404,
        )
        self.assertEqual(self.client.delete(f"/api/v1/widgets/{widget['id']}", headers=bob_headers).status_code, 404)

        embed = self.client.get(f"/api/v1/widgets/{widget['id']}/embed", headers=alice_headers)
        self.assertEqual(embed.status_code, 200, embed.text)
        self.assertIn(widget["public_id"], embed.json()["snippet"])
        self.assertIn("widget.v1.js", embed.json()["snippet"])

    def test_invalid_widget_schema_has_structured_error(self):
        headers = self.login("alice@acme.test")
        response = self.client.post(
            "/api/v1/widgets",
            headers=headers,
            json={"widget_type": "contact", "title": "Bad", "form_fields": [], "button_text": "Go"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_dashboard_is_tenant_scoped(self):
        alice_headers = self.login("alice@acme.test")
        bob_headers = self.login("bob@beta.test")
        alice_summary = self.client.get("/api/v1/dashboard/summary", headers=alice_headers)
        bob_summary = self.client.get("/api/v1/dashboard/summary", headers=bob_headers)
        self.assertEqual(alice_summary.status_code, 200)
        self.assertEqual(bob_summary.status_code, 200)
        self.assertGreaterEqual(alice_summary.json()["total_submissions"], 0)
        self.assertIn("submissions_over_time", alice_summary.json())
        self.assertEqual(bob_summary.json()["total_submissions"], 0)
        self.assertEqual(self.client.get("/api/v1/submissions", headers=bob_headers).json(), [])


if __name__ == "__main__":
    unittest.main()
