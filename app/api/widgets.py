from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.core.config import get_settings
from app.db.models import WidgetWebhook
from app.db.session import get_db
from app.schemas.widgets import EmbedResponse, WidgetCreate, WidgetResponse, WidgetUpdate, WidgetWebhookResponse, WidgetWebhookUpdate
from app.services import widgets as widget_service

router = APIRouter(prefix="/api/v1/widgets", tags=["widgets"])


def not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")


@router.post("", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
def create_widget(payload: WidgetCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return widget_service.create_widget(db, user.tenant_id, payload)


@router.get("", response_model=list[WidgetResponse])
def list_owned_widgets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return widget_service.list_widgets(db, user.tenant_id)


@router.get("/{widget_id}", response_model=WidgetResponse)
def get_widget(widget_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return widget_service.get_owned_widget(db, user.tenant_id, widget_id)
    except widget_service.WidgetNotFoundError:
        raise not_found()


@router.patch("/{widget_id}", response_model=WidgetResponse)
def update_widget(widget_id: str, payload: WidgetUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return widget_service.update_widget(db, user.tenant_id, widget_id, payload)
    except widget_service.WidgetNotFoundError:
        raise not_found()


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(widget_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    try:
        widget_service.deactivate_widget(db, user.tenant_id, widget_id)
    except widget_service.WidgetNotFoundError:
        raise not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{widget_id}/embed", response_model=EmbedResponse)
def get_embed_snippet(widget_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        widget = widget_service.get_owned_widget(db, user.tenant_id, widget_id)
    except widget_service.WidgetNotFoundError:
        raise not_found()
    base_url = get_settings().public_base_url.rstrip("/")
    return EmbedResponse(snippet=f'<script src="{base_url}/widget.v1.js?id={widget.public_id}"></script>')


@router.get("/{widget_id}/webhook", response_model=WidgetWebhookResponse)
def get_widget_webhook(widget_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        widget_service.get_owned_widget(db, user.tenant_id, widget_id)
    except widget_service.WidgetNotFoundError:
        raise not_found()
    webhook = db.query(WidgetWebhook).filter(WidgetWebhook.widget_id == widget_id, WidgetWebhook.tenant_id == user.tenant_id).one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook configuration not found")
    return webhook


@router.put("/{widget_id}/webhook", response_model=WidgetWebhookResponse)
def upsert_widget_webhook(widget_id: str, payload: WidgetWebhookUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        widget_service.get_owned_widget(db, user.tenant_id, widget_id)
    except widget_service.WidgetNotFoundError:
        raise not_found()
    webhook = db.query(WidgetWebhook).filter(WidgetWebhook.widget_id == widget_id, WidgetWebhook.tenant_id == user.tenant_id).one_or_none()
    if webhook is None:
        webhook = WidgetWebhook(widget_id=widget_id, tenant_id=user.tenant_id, **payload.model_dump())
        db.add(webhook)
    else:
        webhook.url = payload.url
        webhook.is_active = payload.is_active
    db.commit()
    db.refresh(webhook)
    return webhook
