from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    id: str
    original_path: Path
    work_dir: Path
    original_filename: str
    source_lang: str
    target_lang: str
    status: str = "validating"
    progress: int = 10
    message: str = "正在分析 PDF"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[Path] = None
    download_token: str = field(default_factory=lambda: uuid4().hex)
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    page_count: Optional[int] = None

    def public_dict(self) -> dict:
        data = {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "page_count": self.page_count,
        }
        if self.status == "completed":
            data["download_url"] = f"/api/download/{self.download_token}"
        if self.status == "failed":
            data["error_code"] = self.error_code
        return data

    def set_state(self, status: str, progress: int, message: str) -> None:
        self.status = status
        self.progress = progress
        self.message = message
        self.updated_at = utcnow()
