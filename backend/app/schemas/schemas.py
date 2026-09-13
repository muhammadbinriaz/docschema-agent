from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreateText(BaseModel):
    text: str = Field(min_length=20)
    filename: str | None = None
    schema_name: str = "invoice"


class FieldPatch(BaseModel):
    value: Any


class FieldOut(BaseModel):
    value: Any
    confidence: float
    uncertain: bool
    edited: bool = False


class JobOut(BaseModel):
    id: UUID
    filename: str | None
    doc_type: str | None
    status: str
    fields: dict[str, FieldOut]
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
