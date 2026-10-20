from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import ImportStatus, IssueStatus


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    file_hash: str
    status: ImportStatus
    stage: str
    progress: float
    data_version_id: UUID | None
    statistics: dict[str, Any]
    error_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImportUploadResult(BaseModel):
    batch: ImportBatchRead
    duplicate_file: bool


class ImportIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    row_no: int | None
    field_name: str | None
    issue_type: str
    raw_value: str | None
    description: str
    status: IssueStatus
