from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("ONLINE_TRANSLATE_SECRET_KEY", "dev-change-me")
    STORAGE_ROOT = Path(os.environ.get("ONLINE_TRANSLATE_STORAGE", BASE_DIR / "storage"))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    MAX_PDF_BYTES = 20 * 1024 * 1024
    MAX_PDF_PAGES = 20
    RETENTION_DAYS = 30
    TRANSLATION_TIMEOUT_SECONDS = int(os.environ.get("ONLINE_TRANSLATE_TIMEOUT", "7200"))

    PDF2ZH_EXE = Path(
        os.environ.get(
            "PDF2ZH_EXE",
            "pdf2zh.exe",
        )
    )
    PDF2ZH_SERVICE = os.environ.get("PDF2ZH_SERVICE", "zhipu")
    PDF2ZH_SOURCE_LANG = os.environ.get("PDF2ZH_SOURCE_LANG", "en")
    PDF2ZH_TARGET_LANG = os.environ.get("PDF2ZH_TARGET_LANG", "zh")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    WTF_CSRF_ENABLED = False
