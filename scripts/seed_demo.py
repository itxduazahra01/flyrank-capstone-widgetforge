"""Seed deterministic tenants/users/widgets for local demo use."""

from pathlib import Path
import sys

# Allow `python scripts/seed_demo.py` from a clean checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Tenant, User, Widget
from app.db.session import Base, SessionLocal, engine

ALICE_EMAIL = "alice@acme.test"
BOB_EMAIL = "bob@beta.test"
DEMO_PASSWORD = "DemoPass123!"


def get_or_create_tenant(db, name: str) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.name == name))
    if tenant is None:
        tenant = Tenant(name=name)
        db.add(tenant)
        db.flush()
    return tenant


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        acme = get_or_create_tenant(db, "Acme Labs")
        beta = get_or_create_tenant(db, "Beta Studio")
        for tenant, email in ((acme, ALICE_EMAIL), (beta, BOB_EMAIL)):
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(tenant_id=tenant.id, email=email, password_hash=hash_password(DEMO_PASSWORD)))
        if db.scalar(select(Widget).where(Widget.tenant_id == acme.id)) is None:
            db.add(
                Widget(
                    tenant_id=acme.id,
                    widget_type="signup",
                    title="Get product updates",
                    description="Monthly product notes, no spam.",
                    form_fields=[
                        {"name": "email", "label": "Work email", "type": "email", "required": True, "max_length": 254},
                        {"name": "name", "label": "Name", "type": "text", "required": False, "max_length": 120},
                    ],
                    button_text="Subscribe",
                    display_options={},
                )
            )
        db.commit()
    print(f"Seeded demo users: {ALICE_EMAIL} and {BOB_EMAIL}; password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
