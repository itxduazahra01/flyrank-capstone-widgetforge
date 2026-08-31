import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


def uuid_str() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    widgets: Mapped[list["Widget"]] = relationship(back_populates="tenant")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Widget(TimestampMixin, Base):
    __tablename__ = "widgets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=uuid_str, index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_fields: Mapped[list] = mapped_column(JSONType, nullable=False)
    button_text: Mapped[str] = mapped_column(String(80), nullable=False)
    display_options: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tenant: Mapped[Tenant] = relationship(back_populates="widgets")

    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_widget_tenant_id"),)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_id: Mapped[str] = mapped_column(ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    source_origin: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    geo_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    spam_status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")
    lead_status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_idempotency"),)


class WidgetEvent(Base):
    __tablename__ = "widget_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_id: Mapped[str] = mapped_column(ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_origin: Mapped[str | None] = mapped_column(String(300), nullable=True)
    session_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class WidgetWebhook(TimestampMixin, Base):
    __tablename__ = "widget_webhooks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_id: Mapped[str] = mapped_column(ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, default="submission.accepted")
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
