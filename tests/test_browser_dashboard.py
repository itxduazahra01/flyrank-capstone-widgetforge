"""Browser proof for the owner dashboard's main extension flows."""
import os
import json
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
APP_URL = "http://127.0.0.1:5173"


@unittest.skipUnless(sync_playwright, "Install requirements-dev.txt to run browser proof")
class DashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            with urlopen("http://127.0.0.1:8000/health", timeout=3):
                pass
        except Exception as exc:
            raise unittest.SkipTest(f"Dashboard proof needs the Compose API: {exc}")
        login = Request(
            "http://127.0.0.1:8000/api/v1/auth/login",
            data=json.dumps({"email": "alice@acme.test", "password": "DemoPass123!"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(login, timeout=5) as response:
            cls.token = json.load(response)["access_token"]
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise unittest.SkipTest("Dashboard proof needs npm")
        cls.process = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1"],
            cwd=FRONTEND,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "CI": "true"},
        )
        for _ in range(40):
            try:
                with urlopen(APP_URL, timeout=1):
                    return
            except Exception:
                time.sleep(0.25)
        cls.process.terminate()
        raise RuntimeError("Vite dashboard did not start")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()

    def test_owner_can_open_extension_workflows(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(APP_URL, wait_until="networkidle")
            page.evaluate("token => sessionStorage.setItem('widgetforge_access_token', token)", self.token)
            page.goto(f"{APP_URL}/dashboard", wait_until="networkidle")
            page.get_by_role("heading", name="Lead capture, visible.").wait_for(timeout=10_000)
            page.get_by_role("button", name="Sign out →").click()
            page.get_by_role("heading", name="Welcome back").wait_for(timeout=5_000)
            page.get_by_label("Email").fill("alice@acme.test")
            page.get_by_label("Password").fill("DemoPass123!")
            page.get_by_role("button", name="Sign in").click()
            page.get_by_role("heading", name="Lead capture, visible.").wait_for(timeout=5_000)
            page.get_by_role("link", name="04 / Explorer").click()
            page.get_by_role("heading", name="Find the right lead.").wait_for(timeout=5_000)
            page.get_by_role("link", name="05 / Lead actions").click()
            page.get_by_role("heading", name="Move leads together.").wait_for(timeout=5_000)
            page.get_by_role("link", name="06 / Integrations").click()
            page.get_by_role("heading", name="Webhook deliveries.").wait_for(timeout=5_000)
            browser.close()
