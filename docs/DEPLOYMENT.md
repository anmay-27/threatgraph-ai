# Running locally

## Docker

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f backend worker
```

UI: http://localhost:3000. API docs: http://localhost:8000/docs. PostgreSQL and Redis are internal; named volumes persist database, queue and upload data. Model artifacts are a read-only bind mount. The backend migrates the schema before serving. The worker waits for API health. Celery beat runs hourly retention cleanup. Docker builds include CPU PyTorch, FFmpeg, Tesseract and C2PA; downloading dependencies can take substantial time. No pretrained task-specific media checkpoint is automatically installed.

Docker now defaults to `AUTH_REQUIRED=true`. Register in the UI, then promote your own account for case management with `docker compose exec backend python scripts/manage_account.py your@email.example --role ANALYST`. Use `ADMIN` for the operations dashboard. Sign out and back in after promotion. Set `SECURE_COOKIES=true` behind HTTPS. Existing local analyses remain unassigned; account mode does not expose them to newly registered users. To keep the original single-user local behavior, set `AUTH_REQUIRED=false` explicitly in `.env`.

The browser extension in `browser-extension/` is an unpacked local preview. It submits only after a click and uses a short-lived token created in the signed-in web app when account mode is enabled. See [extension instructions](../browser-extension/README.md).

Change the local database password before any shared deployment. Compose supplies explicit environment defaults; `.env.example` documents the full application settings. Do not blindly use the Docker database hostname in a non-Docker shell.

To omit PyTorch for a static-analysis-only installation, build with `docker compose build --build-arg INSTALL_ML=false`; model entries remain unavailable until dependencies and trained checkpoints are installed. This option does not provide substitute media predictions.

ClamAV local `clamscan` requires current signature databases. To use the local daemon set `CLAMAV_HOST=clamav` in `.env` and run `docker compose --profile clamav up --build -d`. Without a working database, reports explicitly show unavailable scanner coverage. Do not point this setting at a third-party host; it receives file bytes.

## Native development

For native malware scanning, start Docker Desktop and run `docker compose --profile clamav up -d clamav`. The native API launcher defaults to the loopback daemon at `127.0.0.1:3310`; it reports unavailable coverage when that daemon is stopped. An explicit `CLAMAV_HOST` environment setting overrides this default.

Windows PowerShell from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip install c2pa-python pytesseract
.\.venv\Scripts\python.exe scripts/dev_api.py
```

Second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

If `python` is the Windows Store alias, invoke your installed interpreter by its full path. This environment has Python 3.13 at `C:\Users\DELL\AppData\Local\Programs\Python\Python313\python.exe`. The dev launcher sets SQLite and a bounded local executor. It does not require Redis/PostgreSQL but lacks durable jobs. For native Linux use `.venv/bin/python` and export `PYTHONPATH=backend:.`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm test
npm run build
npm run test:e2e
```

Playwright defaults to installed Microsoft Edge on Windows and Chromium on Linux. Set `THREATGRAPH_PYTHON` or `PLAYWRIGHT_CHANNEL` to override detected defaults; on Linux install the browser with `npx playwright install chromium`. There is no bundled browser binary. Build the frontend before E2E. Tests reuse a running local deployment; otherwise they start the native API with `storage/e2e.db` and a production-preview frontend. They submit real benign test files and save screenshots under `docs/screenshots`.

Docker verification: `python scripts/smoke_deployment.py` uploads image/audio/video/HTML samples through Celery, verifies reports and persistent history, and saves `research/results/docker_smoke.json`. A native thread-mode E2E pass alone does not prove Redis/Celery/PostgreSQL behavior. Both Docker smoke and browser workflows were successfully run on this machine. The optional accessibility test checks all main pages and the mobile submission page; it is an automated check, not a full accessibility certification.
