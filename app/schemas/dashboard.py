from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    widget_id: str
    payload: dict[str, Any]
    geo_country: str | None
    geo_city: str | None
    geo_provider: str | None
    lead_status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SubmissionStatusUpdate(BaseModel):
    lead_status: str


class SubmissionBulkStatusUpdate(BaseModel):
    submission_ids: list[str] = Field(min_length=1, max_length=50)
    lead_status: str


class SubmissionNotesUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class SubmissionPage(BaseModel):
    items: list[SubmissionListItem]
    next_cursor: str | None


class WebhookDeliveryListItem(BaseModel):
    id: str
    submission_id: str
    event_type: str
    status: str
    attempt_count: int
    last_error: str | None
    available_at: datetime
    created_at: datetime


class DashboardSummary(BaseModel):
    total_submissions: int
    widget_views: int
    form_starts: int
    accepted_submissions: int
    conversion_rate: float
    by_widget: list[dict[str, Any]]
    by_country: list[dict[str, Any]]
    submissions_over_time: list[dict[str, Any]]


class DashboardAnalytics(BaseModel):
    days: int
    widget_views: int
    form_starts: int
    accepted_submissions: int
    conversion_rate: float
    events_over_time: list[dict[str, Any]]
    by_origin: list[dict[str, Any]]
    by_country: list[dict[str, Any]]
