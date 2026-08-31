"""Upgrade a fresh database or safely baseline a complete pre-Alembic schema."""
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine

EXPECTED_TABLES = {"tenants", "users", "widgets", "submissions", "outbox_events"}

config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
tables = set(inspect(engine).get_table_names())

if EXPECTED_TABLES.issubset(tables) and "alembic_version" not in tables:
    print("Complete legacy schema found; baselining Alembic at head.", flush=True)
    command.stamp(config, "head")
elif tables & EXPECTED_TABLES and not EXPECTED_TABLES.issubset(tables):
    missing = ", ".join(sorted(EXPECTED_TABLES - tables))
    raise RuntimeError(f"Refusing to migrate a partial legacy schema. Missing: {missing}")
else:
    command.upgrade(config, "head")
