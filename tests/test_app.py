from __future__ import annotations

import io
import threading
import time
from pathlib import Path

import fitz
import pytest

from app.config import TestConfig
from app.main import create_app


def make_pdf(page_count: int = 1) -> io.BytesIO:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"Test page {index + 1}")
    data = doc.tobytes()
    doc.close()
    stream = io.BytesIO(data)
    stream.name = "paper.pdf"
    return stream


class FastTranslator:
    def translate(self, source_pdf: Path, output_dir: Path) -> Path:
        output = output_dir / "source-mono.pdf"
        output.write_bytes(make_pdf().getvalue())
        return output


class BlockingTranslator:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def translate(self, source_pdf: Path, output_dir: Path) -> Path:
        self.started.set()
        self.release.wait(timeout=3)
        output = output_dir / "source-mono.pdf"
        output.write_bytes(make_pdf().getvalue())
        return output


@pytest.fixture
def app(tmp_path):
    class LocalTestConfig(TestConfig):
        STORAGE_ROOT = tmp_path / "storage"

    return create_app(LocalTestConfig, translator=FastTranslator())


@pytest.fixture
def client(app):
    return app.test_client()


def upload(client, pages: int = 1, filename: str = "paper.pdf"):
    return client.post(
        "/api/jobs",
        data={
            "source_lang": "en",
            "target_lang": "zh",
            "pdf": (make_pdf(pages), filename),
        },
        content_type="multipart/form-data",
    )


def wait_for_job(client, job_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        last = response.get_json()
        if last["status"] in {"completed", "failed"}:
            return last
        time.sleep(0.05)
    return last


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_upload_creates_job_and_downloads_translated_pdf(client):
    response = upload(client)
    assert response.status_code == 202
    job = wait_for_job(client, response.get_json()["id"])

    assert job["status"] == "completed"
    assert job["download_url"].startswith("/api/download/")

    download = client.get(job["download_url"])
    assert download.status_code == 200
    assert download.mimetype == "application/pdf"


def test_rejects_more_than_twenty_pages(client):
    response = upload(client, pages=21)
    assert response.status_code == 400
    assert response.get_json()["error"] == "too_many_pages"


def test_second_anonymous_use_requires_login(client):
    first = upload(client)
    assert first.status_code == 202
    wait_for_job(client, first.get_json()["id"])

    second = upload(client)
    assert second.status_code == 401
    assert second.get_json()["error"] == "login_required"

    login = client.post("/api/login")
    assert login.status_code == 200

    third = upload(client)
    assert third.status_code == 202


def test_rejects_new_job_while_global_task_running(tmp_path):
    class LocalTestConfig(TestConfig):
        STORAGE_ROOT = tmp_path / "storage"

    translator = BlockingTranslator()
    app = create_app(LocalTestConfig, translator=translator)
    client = app.test_client()

    first = upload(client)
    assert first.status_code == 202
    assert translator.started.wait(timeout=1)

    second = client.post(
        "/api/jobs",
        data={
            "source_lang": "en",
            "target_lang": "zh",
            "pdf": (make_pdf(), "second.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert second.status_code == 409
    assert second.get_json()["error"] == "busy"

    translator.release.set()
    wait_for_job(client, first.get_json()["id"])
