# Online Translate

A minimal Flask MVP for translating English PDF papers into Chinese PDF files with a local `pdf2zh` / PDFMathTranslate installation.

## Product Scope

This project is built for a limited MVP:

- Upload one PDF at a time.
- Support English to Simplified Chinese only.
- Limit files to 20 pages and 20 MB.
- Allow anonymous users to translate once; later use requires login.
- Run only one translation task at a time.
- Reject new translation requests while another task is running.
- Return a translated-only PDF.
- Keep original and output files for 30 days.

Out of scope for the MVP:

- OCR for scanned PDFs.
- Batch upload.
- Bilingual PDF download.
- Multi-language translation.
- Persistent account system.
- Queueing.
- Paid plans.

## Requirements

- Windows
- Python 3.9+
- A local `pdf2zh.exe` / PDFMathTranslate installation
- A configured translation provider for PDFMathTranslate

Do not commit API keys, local config files, personal paths, or generated storage files to this repository.

## Install

From the project root:

```powershell
python -m pip install -r requirements.txt
```

## Configuration

Set environment variables before running the service:

| Variable | Required | Purpose |
| --- | --- | --- |
| `ONLINE_TRANSLATE_SECRET_KEY` | Recommended | Flask session secret. Set this before public use. |
| `ONLINE_TRANSLATE_STORAGE` | Optional | Upload, output, and job working directory. Defaults to `<project>\storage`. |
| `ONLINE_TRANSLATE_TIMEOUT` | Optional | Translation timeout in seconds. Defaults to `7200`. |
| `PDF2ZH_EXE` | Recommended | Absolute path to local `pdf2zh.exe`. Defaults to `pdf2zh.exe` on `PATH`. |
| `PDF2ZH_SERVICE` | Optional | Translation service. Defaults to `zhipu`. |
| `PDF2ZH_SOURCE_LANG` | Optional | Source language. Defaults to `en`. |
| `PDF2ZH_TARGET_LANG` | Optional | Target language. Defaults to `zh`. |

Example:

```powershell
$env:ONLINE_TRANSLATE_SECRET_KEY="replace-with-a-random-secret"
$env:PDF2ZH_EXE="C:\path\to\pdf2zh.exe"
```

The translation model is controlled by the local PDFMathTranslate provider configuration, not by this Flask app.

## Run Locally

```powershell
python -m flask --app app.main run
```

Open:

```text
http://127.0.0.1:5000/
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

Expected response:

```json
{"busy":false,"ok":true}
```

## Test

```powershell
python -m pytest -q
```

Current baseline:

```text
5 passed
```

## Deployment Notes

The MVP is designed to run on a machine that already has `pdf2zh` and PDFMathTranslate configured.

Recommended MVP deployment path:

1. Run Flask locally on `127.0.0.1:5000`.
2. Expose it with a tunnel tool such as ngrok, frp, or Cloudflare Tunnel.
3. Share the public URL with a small test group only.

For real public exposure, set a strong `ONLINE_TRANSLATE_SECRET_KEY` and avoid running Flask's development server directly as a production service.

## Privacy and Data Handling

Uploaded PDFs are used only to complete the translation service. Original PDFs are retained for 30 days and then deleted. They are not intended for model training, quality analysis, marketing, manual review, or other secondary uses.

Do not upload highly sensitive documents during MVP testing.

## Known Limitations

- Real `pdf2zh` end-to-end translation should be verified in the target deployment environment.
- Login is a temporary session-based MVP login, not a real account system.
- Job state is in memory and is lost if the Flask process restarts.
- The single-task lock works for a single Flask process only.
- File cleanup is triggered during job creation, not by an independent scheduler.
- `ONLINE_TRANSLATE_SECRET_KEY` must be set before public exposure.
