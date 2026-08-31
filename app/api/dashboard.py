import csv
import base64
import json
from datetime import datetime, timedelta, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.models import OutboxEvent, Submission, Widget, WidgetEvent
from app.db.session import get_db
from app.schemas.dashboard import DashboardAnalytics, DashboardSummary, SubmissionBulkStatusUpdate, SubmissionListItem, SubmissionNotesUpdate, SubmissionPage, SubmissionStatusUpdate, WebhookDeliveryListItem

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _cursor_for(submission: Submission) -> str:
    payload = json.dumps({"created_at": submission.created_at.isoformat(), "id": submission.id}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(payload["created_at"]), payload["id"]
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="Invalid pagination cursor")


@router.get("/submissions", response_model=list[SubmissionListItem])
def list_submissions(
    widget_id: str | None = None,
    lead_status: str | None = None,
    country: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Submission).where(Submission.tenant_id == user.tenant_id)
    if widget_id:
        statement = statement.where(Submission.widget_id == widget_id)
    if lead_status:
        statement = statement.where(Submission.lead_status == lead_status)
    if country:
        statement = statement.where(Submission.geo_country == country)
    if created_after:
        statement = statement.where(Submission.created_at >= created_after)
    if created_before:
        statement = statement.where(Submission.created_at <= created_before)
    return list(db.scalars(statement.order_by(Submission.created_at.desc()).limit(limit)))


@router.get("/submissions/page", response_model=SubmissionPage)
def list_submissions_page(
    widget_id: str | None = None,
    lead_status: str | None = None,
    country: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Submission).where(Submission.tenant_id == user.tenant_id)
    if widget_id:
        statement = statement.where(Submission.widget_id == widget_id)
    if lead_status:
        statement = statement.where(Submission.lead_status == lead_status)
    if country:
        statement = statement.where(Submission.geo_country == country)
    if created_after:
        statement = statement.where(Submission.created_at >= created_after)
    if created_before:
        statement = statement.where(Submission.created_at <= created_before)
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        statement = statement.where(or_(Submission.created_at < cursor_time, and_(Submission.created_at == cursor_time, Submission.id < cursor_id)))
    rows = list(db.scalars(statement.order_by(Submission.created_at.desc(), Submission.id.desc()).limit(limit + 1)))
    has_more = len(rows) > limit
    items = rows[:limit]
    return SubmissionPage(items=items, next_cursor=_cursor_for(items[-1]) if has_more and items else None)


@router.get("/submissions/export")
def export_submissions(
    lead_status: str | None = None,
    widget_id: str | None = None,
    country: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Submission).where(Submission.tenant_id == user.tenant_id)
    if lead_status:
        statement = statement.where(Submission.lead_status == lead_status)
    if widget_id:
        statement = statement.where(Submission.widget_id == widget_id)
    if country:
        statement = statement.where(Submission.geo_country == country)
    if created_after:
        statement = statement.where(Submission.created_at >= created_after)
    if created_before:
        statement = statement.where(Submission.created_at <= created_before)
    rows = list(db.scalars(statement.order_by(Submission.created_at.desc()).limit(10_000)))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["submission_id", "created_at", "lead_status", "name", "email", "country", "city"])
    for row in rows:
        # Prefix spreadsheet formulas so exports cannot execute user-provided values.
        def safe(value: str | None) -> str:
            value = value or ""
            return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value
        writer.writerow([row.id, row.created_at.isoformat(), row.lead_status, safe(row.payload.get("name")), safe(row.payload.get("email")), safe(row.geo_country), safe(row.geo_city)])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=widgetforge-submissions.csv"})


@router.patch("/submissions/{submission_id}/status", response_model=SubmissionListItem)
def update_submission_status(
    submission_id: str,
    payload: SubmissionStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = {"new", "contacted", "qualified", "closed"}
    if payload.lead_status not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported lead status")
    submission = db.scalar(select(Submission).where(Submission.id == submission_id, Submission.tenant_id == user.tenant_id))
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission.lead_status = payload.lead_status
    db.commit()
    db.refresh(submission)
    return submission


@router.patch("/submissions/bulk-status")
def update_submission_bulk_status(
    payload: SubmissionBulkStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = {"new", "contacted", "qualified", "closed"}
    if payload.lead_status not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported lead status")
    ids = list(dict.fromkeys(payload.submission_ids))
    submissions = list(db.scalars(select(Submission).where(Submission.id.in_(ids), Submission.tenant_id == user.tenant_id)))
    if len(submissions) != len(ids):
        raise HTTPException(status_code=404, detail="One or more submissions were not found")
    for submission in submissions:
        submission.lead_status = payload.lead_status
    db.commit()
    return {"updated": len(submissions), "lead_status": payload.lead_status}


@router.patch("/submissions/{submission_id}/notes", response_model=SubmissionListItem)
def update_submission_notes(
    submission_id: str,
    payload: SubmissionNotesUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = db.scalar(select(Submission).where(Submission.id == submission_id, Submission.tenant_id == user.tenant_id))
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission.notes = payload.notes.strip() if payload.notes else None
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/webhook-deliveries", response_model=list[WebhookDeliveryListItem])
def list_webhook_deliveries(
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(OutboxEvent)
        .join(Submission, Submission.id == OutboxEvent.submission_id)
        .where(Submission.tenant_id == user.tenant_id)
        .order_by(OutboxEvent.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/dashboard/analytics", response_model=DashboardAnalytics)
def dashboard_analytics(
    days: int = Query(default=30, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    event_counts = dict(db.execute(
        select(WidgetEvent.event_type, func.count(WidgetEvent.id))
        .where(WidgetEvent.tenant_id == user.tenant_id, WidgetEvent.created_at >= since)
        .group_by(WidgetEvent.event_type)
    ).all())
    views = event_counts.get("widget_viewed", 0)
    starts = event_counts.get("form_started", 0)
    accepted = event_counts.get("submission_accepted", 0)
    day = func.date(WidgetEvent.created_at)
    event_rows = db.execute(
        select(day.label("day"), WidgetEvent.event_type, func.count(WidgetEvent.id).label("count"))
        .where(WidgetEvent.tenant_id == user.tenant_id, WidgetEvent.created_at >= since)
        .group_by(day, WidgetEvent.event_type)
        .order_by(day)
    ).all()
    origin_rows = db.execute(
        select(WidgetEvent.source_origin, func.count(WidgetEvent.id).label("count"))
        .where(WidgetEvent.tenant_id == user.tenant_id, WidgetEvent.created_at >= since)
        .group_by(WidgetEvent.source_origin)
        .order_by(func.count(WidgetEvent.id).desc())
        .limit(10)
    ).all()
    country_rows = db.execute(
        select(Submission.geo_country, func.count(Submission.id).label("count"))
        .where(Submission.tenant_id == user.tenant_id, Submission.created_at >= since)
        .group_by(Submission.geo_country)
        .order_by(func.count(Submission.id).desc())
        .limit(10)
    ).all()
    return DashboardAnalytics(
        days=days,
        widget_views=views,
        form_starts=starts,
        accepted_submissions=accepted,
        conversion_rate=round((accepted / views * 100), 1) if views else 0.0,
        events_over_time=[{"date": str(row.day), "event_type": row.event_type, "count": row.count} for row in event_rows],
        by_origin=[{"origin": row.source_origin or "Unknown", "count": row.count} for row in origin_rows],
        by_country=[{"country": row.geo_country or "Unknown", "count": row.count} for row in country_rows],
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Submission).where(Submission.tenant_id == user.tenant_id)) or 0
    event_counts = dict(db.execute(
        select(WidgetEvent.event_type, func.count(WidgetEvent.id))
        .where(WidgetEvent.tenant_id == user.tenant_id)
        .group_by(WidgetEvent.event_type)
    ).all())
    views = event_counts.get("widget_viewed", 0)
    starts = event_counts.get("form_started", 0)
    accepted = event_counts.get("submission_accepted", 0)
    by_widget_rows = db.execute(
        select(Widget.id, Widget.title, func.count(Submission.id).label("count"))
        .outerjoin(Submission, Submission.widget_id == Widget.id)
        .where(Widget.tenant_id == user.tenant_id)
        .group_by(Widget.id, Widget.title)
        .order_by(func.count(Submission.id).desc())
    ).all()
    by_country_rows = db.execute(
        select(Submission.geo_country, func.count(Submission.id).label("count"))
        .where(Submission.tenant_id == user.tenant_id)
        .group_by(Submission.geo_country)
        .order_by(func.count(Submission.id).desc())
    ).all()
    # SQLAlchemy renders a portable date expression for both the SQLite test
    # database and PostgreSQL used by Compose.
    day = func.date(Submission.created_at)
    over_time_rows = db.execute(
        select(day.label("day"), func.count(Submission.id).label("count"))
        .where(Submission.tenant_id == user.tenant_id)
        .group_by(day)
        .order_by(day)
    ).all()
    return DashboardSummary(
        total_submissions=total,
        widget_views=views,
        form_starts=starts,
        accepted_submissions=accepted,
        conversion_rate=round((accepted / views * 100), 1) if views else 0.0,
        by_widget=[{"widget_id": row.id, "title": row.title, "count": row.count} for row in by_widget_rows],
        by_country=[{"country": row.geo_country or "Unknown", "count": row.count} for row in by_country_rows],
        submissions_over_time=[{"date": str(row.day), "count": row.count} for row in over_time_rows],
    )
