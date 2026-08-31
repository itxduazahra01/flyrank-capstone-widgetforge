from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import WidgetEvent
from app.schemas.public import PublicWidgetConfig, SubmissionRequest, SubmissionResponse, WidgetEventRequest
from app.schemas.widgets import WidgetAppearance
from app.services.submission import accept_submission, analytics_limiter, get_active_widget, hash_ip

router = APIRouter(tags=["public"])


@router.get("/public/v1/widgets/{public_id}/config", response_model=PublicWidgetConfig)
def public_config(public_id: str, request: Request, db: Session = Depends(get_db)):
    widget = get_active_widget(db, public_id)
    appearance = WidgetAppearance.model_validate(widget.display_options or {})
    origin = request.headers.get("origin")
    if appearance.allowed_origins and origin and origin not in appearance.allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This widget is not allowed on this origin")
    etag = f'"widget-{widget.public_id}-{widget.config_version}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    response = PublicWidgetConfig(id=widget.public_id, widget_type=widget.widget_type, title=widget.title, description=widget.description, form_fields=widget.form_fields, button_text=widget.button_text, display_options=appearance.model_dump())
    return Response(content=response.model_dump_json(), media_type="application/json", headers={"Cache-Control": "public, max-age=300, must-revalidate", "ETag": etag})


@router.post("/public/v1/events", status_code=status.HTTP_204_NO_CONTENT)
def capture_event(public_request: WidgetEventRequest, request: Request, db: Session = Depends(get_db)):
    widget = get_active_widget(db, public_request.widget_id)
    appearance = WidgetAppearance.model_validate(widget.display_options or {})
    origin = request.headers.get("origin")
    if appearance.allowed_origins and origin not in appearance.allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This widget is not allowed on this origin")
    session_hash = hash_ip(f"event:{public_request.session_id}")
    analytics_limiter.check(f"analytics:{session_hash}:{widget.public_id}")
    existing = db.scalar(select(WidgetEvent.id).where(WidgetEvent.widget_id == widget.id, WidgetEvent.event_type == public_request.event_type, WidgetEvent.session_hash == session_hash))
    if existing:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    db.add(WidgetEvent(tenant_id=widget.tenant_id, widget_id=widget.id, event_type=public_request.event_type, source_origin=origin, session_hash=session_hash))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/public/v1/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit(public_request: SubmissionRequest, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=64), db: Session = Depends(get_db)):
    widget = get_active_widget(db, public_request.widget_id)
    appearance = WidgetAppearance.model_validate(widget.display_options or {})
    origin = request.headers.get("origin")
    if appearance.allowed_origins and origin not in appearance.allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This widget is not allowed on this origin")
    ip = request.client.host if request.client else "unknown"
    submission, replayed = accept_submission(db, public_id=public_request.widget_id, fields=public_request.fields, honeypot=public_request.website, idempotency_key=idempotency_key, ip=ip, origin=origin)
    if submission is None:
        return SubmissionResponse(id="", status="accepted")
    return SubmissionResponse(id=submission.id, replayed=replayed)
