from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Widget
from app.schemas.widgets import WidgetCreate, WidgetUpdate


class WidgetNotFoundError(Exception):
    pass


def list_widgets(db: Session, tenant_id: str) -> list[Widget]:
    return list(db.scalars(select(Widget).where(Widget.tenant_id == tenant_id).order_by(Widget.created_at.desc())))


def get_owned_widget(db: Session, tenant_id: str, widget_id: str) -> Widget:
    widget = db.scalar(select(Widget).where(Widget.id == widget_id, Widget.tenant_id == tenant_id))
    if widget is None:
        raise WidgetNotFoundError
    return widget


def create_widget(db: Session, tenant_id: str, payload: WidgetCreate) -> Widget:
    widget = Widget(tenant_id=tenant_id, **payload.model_dump())
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


def update_widget(db: Session, tenant_id: str, widget_id: str, payload: WidgetUpdate) -> Widget:
    widget = get_owned_widget(db, tenant_id, widget_id)
    changes = payload.model_dump(exclude_unset=True)
    public_fields = {"widget_type", "title", "description", "form_fields", "button_text", "display_options", "is_active"}
    if public_fields.intersection(changes):
        widget.config_version += 1
    for key, value in changes.items():
        setattr(widget, key, value)
    db.commit()
    db.refresh(widget)
    return widget


def deactivate_widget(db: Session, tenant_id: str, widget_id: str) -> None:
    widget = get_owned_widget(db, tenant_id, widget_id)
    widget.is_active = False
    widget.config_version += 1
    db.commit()
