from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RESERVED_FIELD_NAMES = {"website", "widget_id", "fields"}


class FormField(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=80)
    type: Literal["text", "email"]
    required: bool = False
    max_length: int = Field(default=120, ge=1, le=254)

    @field_validator("name")
    @classmethod
    def name_must_not_be_reserved(cls, value: str) -> str:
        if value in RESERVED_FIELD_NAMES:
            raise ValueError("Field name is reserved")
        return value


class WidgetAppearance(BaseModel):
    """Safe, intentionally small theming surface for a public embedded form."""
    model_config = ConfigDict(extra="forbid")
    primary_color: str = Field(default="#2457E6", pattern=r"^#[0-9A-Fa-f]{6}$")
    border_radius: int = Field(default=8, ge=0, le=24)
    success_message: str = Field(default="Your submission was received.", min_length=1, max_length=160)
    allowed_origins: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("allowed_origins")
    @classmethod
    def allowed_origins_must_be_http_origins(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            origin = value.rstrip("/")
            if not (origin.startswith("http://") or origin.startswith("https://")) or "/" in origin.split("://", 1)[1]:
                raise ValueError("Allowed origins must be origins such as https://example.com")
            normalized.append(origin)
        if len(normalized) != len(set(normalized)):
            raise ValueError("Allowed origins must be unique")
        return normalized


class WidgetBase(BaseModel):
    widget_type: Literal["signup", "contact"]
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    form_fields: list[FormField] = Field(min_length=1, max_length=8)
    button_text: str = Field(min_length=1, max_length=80)
    display_options: WidgetAppearance = Field(default_factory=WidgetAppearance)

    @model_validator(mode="after")
    def field_names_are_unique(self):
        names = [field.name for field in self.form_fields]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique")
        return self


class WidgetCreate(WidgetBase):
    pass


class WidgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    widget_type: Literal["signup", "contact"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    form_fields: list[FormField] | None = Field(default=None, min_length=1, max_length=8)
    button_text: str | None = Field(default=None, min_length=1, max_length=80)
    display_options: WidgetAppearance | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def update_field_names_are_unique(self):
        if self.form_fields is not None:
            names = [field.name for field in self.form_fields]
            if len(names) != len(set(names)):
                raise ValueError("Field names must be unique")
        return self


class WidgetResponse(WidgetBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    public_id: str
    is_active: bool
    config_version: int


class EmbedResponse(BaseModel):
    snippet: str


class WidgetWebhookUpdate(BaseModel):
    url: str = Field(min_length=12, max_length=500, pattern=r"^https://")
    is_active: bool = True


class WidgetWebhookResponse(WidgetWebhookUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    widget_id: str
