"""Run the durable notification worker as a separate Compose service."""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.workers.outbox import process_pending_events


while True:
    with SessionLocal() as db:
        processed = process_pending_events(db)
        if processed:
            print(f"Processed {processed} outbox event(s)", flush=True)
    time.sleep(get_settings().outbox_poll_seconds)
