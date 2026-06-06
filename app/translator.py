from __future__ import annotations

import re
import subprocess
from pathlib import Path


class TranslationError(Exception):
    pass


class Pdf2ZhTranslator:
    def __init__(
        self,
        exe: Path,
        service: str,
        source_lang: str,
        target_lang: str,
        timeout_seconds: int,
    ):
        self.exe = exe
        self.service = service
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timeout_seconds = timeout_seconds

    def translate(self, source_pdf: Path, output_dir: Path) -> Path:
        if not self.exe.exists():
            raise TranslationError(f"pdf2zh executable not found: {self.exe}")

        started_mtime_floor = source_pdf.stat().st_mtime
        command = [
            str(self.exe),
            str(source_pdf),
            "-s",
            self.service,
            "-li",
            self.source_lang,
            "-lo",
            self.target_lang,
            "-t",
            "1",
            "-o",
            str(output_dir),
        ]

        log_path = output_dir / "_translate.log"
        try:
            completed = subprocess.run(
                command,
                cwd=output_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TranslationError("translation_timeout") from exc

        log_text = completed.stdout or ""
        log_path.write_text(log_text, encoding="utf-8", errors="replace")

        if re.search(r"\b(429|1302|ERROR)\b", log_text, re.IGNORECASE):
            raise TranslationError("translation_api_error")

        mono_pdf = output_dir / f"{source_pdf.stem}-mono.pdf"
        if not mono_pdf.exists():
            raise TranslationError("missing_output")

        if mono_pdf.stat().st_mtime < started_mtime_floor:
            raise TranslationError("stale_output")

        if mono_pdf.stat().st_size <= 0:
            raise TranslationError("empty_output")

        return mono_pdf
