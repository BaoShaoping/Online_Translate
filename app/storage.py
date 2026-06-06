from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import fitz
from werkzeug.datastructures import FileStorage

from .models import utcnow


class UploadValidationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def ensure_storage(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


def create_work_dir(root: Path) -> Path:
    ensure_storage(root)
    work_dir = root / uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=False)
    return work_dir


def save_upload(upload: FileStorage, work_dir: Path, max_bytes: int) -> Path:
    if not upload or not upload.filename:
        raise UploadValidationError("missing_file", "请上传 PDF 文件。")

    if not upload.filename.lower().endswith(".pdf"):
        raise UploadValidationError("invalid_type", "请上传 PDF 文件。")

    target = work_dir / "source.pdf"
    upload.save(target)

    if target.stat().st_size <= 0:
        raise UploadValidationError("empty_file", "PDF 文件为空。")

    if target.stat().st_size > max_bytes:
        raise UploadValidationError("file_too_large", "请上传 20 页以内、20MB 以内的 PDF。")

    return target


def validate_pdf(path: Path, max_pages: int) -> int:
    try:
        with fitz.open(path) as doc:
            if doc.is_encrypted:
                raise UploadValidationError("encrypted_pdf", "暂不支持加密 PDF。")
            if doc.page_count <= 0:
                raise UploadValidationError("invalid_pdf", "PDF 没有可读取页面。")
            if doc.page_count > max_pages:
                raise UploadValidationError("too_many_pages", "请上传 20 页以内、20MB 以内的 PDF。")
            return doc.page_count
    except UploadValidationError:
        raise
    except Exception as exc:
        raise UploadValidationError("invalid_pdf", "这个 PDF 暂时无法解析，请更换文件后重试。") from exc


def cleanup_expired(root: Path, retention_days: int) -> int:
    if not root.exists():
        return 0

    cutoff = utcnow() - timedelta(days=retention_days)
    removed = 0
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = child.stat().st_mtime
            modified_at = utcnow().fromtimestamp(mtime, tz=utcnow().tzinfo)
            if modified_at < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed
