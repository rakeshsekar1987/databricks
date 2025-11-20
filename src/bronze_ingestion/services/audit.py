"""
Audit logging utilities persisting run metadata to Delta tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..logging_utils import StructuredLogger
from ..metadata.models import AuditRecord, LoadMode, TableMetadata
from ..metadata.provider import MetadataProvider


@dataclass
class AuditHandle:
    record: AuditRecord


class AuditService:
    def __init__(self, provider: MetadataProvider, logger: StructuredLogger):
        self._provider = provider
        self._logger = logger

    def start_table(self, table: TableMetadata, mode: LoadMode, run_id: str) -> AuditHandle:
        record = AuditRecord(
            run_id=run_id,
            table_name=table.table_name,
            source_table=table.full_table_name,
            mode=mode,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            rows_read=0,
            rows_written=0,
            status="RUNNING",
        )
        self._logger.info(
            "audit.start",
            {"table": table.table_name, "mode": mode.value, "run_id": run_id},
        )
        return AuditHandle(record=record)

    def complete(
        self,
        handle: AuditHandle,
        rows_read: int,
        rows_written: int,
        status: str,
        error_message: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ):
        end_time = datetime.now(timezone.utc)
        auto_duration = (end_time - handle.record.start_time).total_seconds()
        duration_seconds = duration_seconds or auto_duration
        throughput = rows_written / duration_seconds if duration_seconds > 0 else None
        completed = AuditRecord(
            **{
                **handle.record.__dict__,
                "rows_read": rows_read,
                "rows_written": rows_written,
                "status": status,
                "end_time": end_time,
                "error_message": error_message,
                "throughput_rows_per_sec": throughput,
            }
        )
        self._provider.record_audit(completed)
        self._logger.info(
            "audit.complete",
            {
                "table": handle.record.table_name,
                "status": status,
                "rows_written": rows_written,
                "duration_seconds": duration_seconds,
            },
        )
