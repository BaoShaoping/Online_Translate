from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .models import Job, utcnow


class JobManager:
    def __init__(self, translator):
        self._translator = translator
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._token_to_job: dict[str, str] = {}
        self._active_job_id: Optional[str] = None

    def is_busy(self) -> bool:
        with self._lock:
            return self._active_job_id is not None

    def create_job(
        self,
        original_path: Path,
        work_dir: Path,
        original_filename: str,
        source_lang: str,
        target_lang: str,
        page_count: int,
    ) -> Optional[Job]:
        with self._lock:
            if self._active_job_id is not None:
                return None

            job = Job(
                id=uuid4().hex,
                original_path=original_path,
                work_dir=work_dir,
                original_filename=original_filename,
                source_lang=source_lang,
                target_lang=target_lang,
                page_count=page_count,
            )
            self._jobs[job.id] = job
            self._token_to_job[job.download_token] = job.id
            self._active_job_id = job.id

        thread = threading.Thread(target=self._run_job, args=(job.id,), daemon=True)
        thread.start()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_job_by_token(self, token: str) -> Optional[Job]:
        with self._lock:
            job_id = self._token_to_job.get(token)
            if not job_id:
                return None
            return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if not job:
            return

        self._update(job_id, "translating", 25, "正在翻译文本")
        job.started_at = utcnow()
        try:
            output = self._translator.translate(job.original_path, job.work_dir)
            self._update(job_id, "generating", 90, "正在生成译文 PDF")
            with self._lock:
                job.output_path = output
                job.completed_at = utcnow()
                job.set_state("completed", 100, "翻译完成")
        except Exception as exc:
            with self._lock:
                job.error_code = "translation_failed"
                job.error_detail = str(exc)
                job.set_state(
                    "failed",
                    100,
                    "这个 PDF 暂时无法翻译，请更换文件后重试。",
                )
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def _update(self, job_id: str, status: str, progress: int, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.set_state(status, progress, message)
