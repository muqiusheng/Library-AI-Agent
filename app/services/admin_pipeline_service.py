import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import (
    DataVersion,
    DataVersionStatus,
    ImportBatch,
    ImportIssue,
    ImportStatus,
)
from app.db.session import SessionLocal
from app.pipelines.import_excel import ExcelLibraryImporter
from app.pipelines.index import BookIndexService
from app.pipelines.tag import RuleTaggingService


class AdminPipelineService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def accept_upload(self, file_name: str, content: bytes) -> tuple[ImportBatch, bool]:
        safe_name = Path(file_name).name
        if not safe_name.lower().endswith(".xlsx"):
            raise AppError(status_code=415, code="INVALID_FILE_TYPE", message="仅支持 .xlsx 文件")
        if not content or len(content) > self.settings.import_max_bytes:
            raise AppError(
                status_code=413, code="FILE_SIZE_INVALID", message="文件为空或超过大小限制"
            )
        if not content.startswith(b"PK"):
            raise AppError(status_code=415, code="INVALID_XLSX", message="文件不是有效的 XLSX 容器")
        file_hash = hashlib.sha256(content).hexdigest()
        existing = self.session.scalar(
            select(ImportBatch).where(ImportBatch.file_hash == file_hash)
        )
        if existing is not None:
            return existing, True
        directory = Path(self.settings.import_upload_directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        stored_path = directory / f"{uuid4().hex}.xlsx"
        stored_path.write_bytes(content)
        batch = ImportBatch(
            file_name=safe_name,
            file_hash=file_hash,
            stored_path=str(stored_path),
            status=ImportStatus.PENDING,
            stage="uploaded",
            progress=0,
            statistics={},
        )
        self.session.add(batch)
        self.session.commit()
        return batch, False

    def list_batches(self) -> list[ImportBatch]:
        return list(
            self.session.scalars(
                select(ImportBatch).order_by(desc(ImportBatch.created_at)).limit(50)
            )
        )

    def get_batch(self, batch_id: UUID) -> ImportBatch:
        batch = self.session.get(ImportBatch, batch_id)
        if batch is None:
            raise AppError(status_code=404, code="IMPORT_BATCH_NOT_FOUND", message="导入批次不存在")
        return batch

    def list_issues(self, batch_id: UUID, limit: int, offset: int) -> list[ImportIssue]:
        self.get_batch(batch_id)
        return list(
            self.session.scalars(
                select(ImportIssue)
                .where(ImportIssue.batch_id == batch_id)
                .order_by(ImportIssue.row_no)
                .offset(offset)
                .limit(limit)
            )
        )

    def queue_publish(self, batch_id: UUID) -> ImportBatch:
        batch = self.get_batch(batch_id)
        if batch.status != ImportStatus.SUCCEEDED or batch.data_version_id is None:
            raise AppError(
                status_code=409, code="IMPORT_NOT_READY", message="导入批次尚未准备好发布"
            )
        version = self.session.get(DataVersion, batch.data_version_id)
        if version is None or version.status != DataVersionStatus.DRAFT:
            raise AppError(
                status_code=409, code="VERSION_NOT_DRAFT", message="数据版本不是待发布状态"
            )
        batch.status = ImportStatus.RUNNING
        batch.stage = "tagging"
        batch.progress = 70
        batch.error_summary = None
        self.session.commit()
        return batch

    @staticmethod
    def run_import(batch_id: UUID) -> None:
        with SessionLocal() as session:
            batch = session.get(ImportBatch, batch_id)
            if batch is None:
                return
            try:
                ExcelLibraryImporter(session).import_file(batch.stored_path, publish=False)
            except Exception:
                # Importer persists a stable failure summary on the batch.
                return

    @staticmethod
    def run_publish(batch_id: UUID) -> None:
        with SessionLocal() as session:
            batch = session.get(ImportBatch, batch_id)
            if batch is None or batch.data_version_id is None:
                return
            version = session.get(DataVersion, batch.data_version_id)
            try:
                RuleTaggingService(session).run(batch.data_version_id)
                batch = session.get(ImportBatch, batch_id)
                batch.stage = "indexing"
                batch.progress = 85
                session.commit()
                BookIndexService(session).build(batch.data_version_id)
                current = list(
                    session.scalars(
                        select(DataVersion).where(
                            DataVersion.status == DataVersionStatus.PUBLISHED,
                            DataVersion.id != batch.data_version_id,
                        )
                    )
                )
                for published in current:
                    published.status = DataVersionStatus.ARCHIVED
                version.status = DataVersionStatus.PUBLISHED
                version.published_at = datetime.now(UTC)
                batch.status = ImportStatus.SUCCEEDED
                batch.stage = "published"
                batch.progress = 100
                batch.finished_at = datetime.now(UTC)
                session.commit()
            except Exception as exc:
                session.rollback()
                batch = session.get(ImportBatch, batch_id)
                version = session.get(DataVersion, batch.data_version_id) if batch else None
                if batch:
                    batch.status = ImportStatus.FAILED
                    batch.error_summary = f"{exc.__class__.__name__}: {exc}"[:2000]
                    batch.finished_at = datetime.now(UTC)
                if version:
                    version.status = DataVersionStatus.FAILED
                session.commit()
