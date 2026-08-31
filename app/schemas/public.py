from typing import Any, Literal
from pydantic import BaseModel, Field


class SubmissionRequest(BaseModel):
    widget_id: str = Field(min_length=36, max_length=36)
    fields: dict[str, Any] = Field(min_length=1, max_length=8)
    website: str = Field(default="", max_length=200)


class SubmissionResponse(BaseModel):
    id: str
    status: str = "accepted"
    replayed: bool = False


class WidgetEventRequest(BaseModel):
    widget_id: str = Field(min_length=36, max_length=36)
    event_type: Literal["widget_viewed", "form_started"]
    session_id: str = Field(min_length=8, max_length=100)


class PublicWidgetConfig(BaseModel):
    id: str
    widget_type: str
    title: str
    description: str | None
    form_fields: list[dict]
    button_text: str
    display_options: dict
