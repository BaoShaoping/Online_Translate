from __future__ import annotations

import shutil
from pathlib import Path

from flask import Flask, jsonify, request, send_file, session
from werkzeug.exceptions import RequestEntityTooLarge

from .config import Config
from .jobs import JobManager
from .storage import (
    UploadValidationError,
    cleanup_expired,
    create_work_dir,
    save_upload,
    validate_pdf,
)
from .translator import Pdf2ZhTranslator


def create_app(config_object: type[Config] = Config, translator=None) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
        static_url_path="",
    )
    app.config.from_object(config_object)

    if translator is None:
        translator = Pdf2ZhTranslator(
            exe=app.config["PDF2ZH_EXE"],
            service=app.config["PDF2ZH_SERVICE"],
            source_lang=app.config["PDF2ZH_SOURCE_LANG"],
            target_lang=app.config["PDF2ZH_TARGET_LANG"],
            timeout_seconds=app.config["TRANSLATION_TIMEOUT_SECONDS"],
        )

    manager = JobManager(translator)
    app.extensions["job_manager"] = manager

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "busy": manager.is_busy()})

    @app.get("/api/me")
    def me():
        return jsonify(
            {
                "authenticated": bool(session.get("authenticated")),
                "anonymous_used": bool(session.get("anonymous_used")),
            }
        )

    @app.post("/api/login")
    def login():
        session["authenticated"] = True
        return jsonify({"ok": True, "authenticated": True})

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.post("/api/jobs")
    def create_job():
        cleanup_expired(app.config["STORAGE_ROOT"], app.config["RETENTION_DAYS"])

        if manager.is_busy():
            return (
                jsonify(
                    {
                        "error": "busy",
                        "message": "当前有文件正在翻译，请稍后再试。",
                    }
                ),
                409,
            )

        if not session.get("authenticated") and session.get("anonymous_used"):
            return (
                jsonify(
                    {
                        "error": "login_required",
                        "message": "登录后可继续使用免费翻译。",
                    }
                ),
                401,
            )

        work_dir = create_work_dir(app.config["STORAGE_ROOT"])
        try:
            upload = request.files.get("pdf")
            source_lang = request.form.get("source_lang", "en")
            target_lang = request.form.get("target_lang", "zh")
            if source_lang != "en" or target_lang != "zh":
                raise UploadValidationError("unsupported_language", "MVP 当前仅支持英文到中文。")

            source_pdf = save_upload(upload, work_dir, app.config["MAX_PDF_BYTES"])
            page_count = validate_pdf(source_pdf, app.config["MAX_PDF_PAGES"])

            job = manager.create_job(
                original_path=source_pdf,
                work_dir=work_dir,
                original_filename=upload.filename,
                source_lang=source_lang,
                target_lang=target_lang,
                page_count=page_count,
            )
            if job is None:
                shutil.rmtree(work_dir, ignore_errors=True)
                return (
                    jsonify(
                        {
                            "error": "busy",
                            "message": "当前有文件正在翻译，请稍后再试。",
                        }
                    ),
                    409,
                )

            if not session.get("authenticated"):
                session["anonymous_used"] = True

            return jsonify(job.public_dict()), 202
        except UploadValidationError as exc:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({"error": exc.code, "message": exc.message}), 400
        except Exception:
            shutil.rmtree(work_dir, ignore_errors=True)
            return (
                jsonify(
                    {
                        "error": "server_error",
                        "message": "这个 PDF 暂时无法翻译，请更换文件后重试。",
                    }
                ),
                500,
            )

    @app.get("/api/jobs/<job_id>")
    def get_job(job_id: str):
        job = manager.get_job(job_id)
        if not job:
            return jsonify({"error": "not_found", "message": "任务不存在。"}), 404
        return jsonify(job.public_dict())

    @app.get("/api/download/<token>")
    def download(token: str):
        job = manager.get_job_by_token(token)
        if not job or job.status != "completed" or not job.output_path:
            return jsonify({"error": "not_found", "message": "文件不存在或尚未生成。"}), 404
        return send_file(
            job.output_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="translated.pdf",
        )

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return (
            jsonify(
                {
                    "error": "file_too_large",
                    "message": "文件超过限制，请上传 20 页以内、20MB 以内的 PDF。",
                }
            ),
            413,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
