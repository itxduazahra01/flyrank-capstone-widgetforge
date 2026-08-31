from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.workers.outbox import process_pending_events

with SessionLocal() as db:
    print(f"Processed {process_pending_events(db)} outbox event(s)")
