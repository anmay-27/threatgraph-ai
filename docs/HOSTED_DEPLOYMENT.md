# Noncommercial hosted MVP

The Render Blueprint creates one Singapore web service using the Standard (1 CPU, 2 GB) plan and a 5 GB disk. Published base pricing checked during preparation: $25/month compute plus $1.25/month disk, excluding taxes, extra bandwidth and build usage. This is an initial demonstration configuration; memory and latency must be checked on the live service before claiming capacity. Analysis concurrency is one and uploads are limited to 50 MB on this hosted profile.

The container builds the frontend, installs FFmpeg and Tesseract, downloads the pinned image and video checkpoints with checksum verification, and serves the frontend and API on the same HTTPS origin. The image weights retain their noncommercial license. Model cards are downloaded with the weights. No audio authenticity checkpoint is installed; video remains experimental. No antivirus service is included in this initial profile, so malware signature coverage will be shown as unavailable. Static URL/document checks still run.

Accounts, session hashes, investigations and uploads are stored on the disk under /app/storage. Local laptop data is not copied. The SQLite profile is limited to one service instance. Deployments interrupt active analyses; those jobs become failed and can be retried. Export important reports and make database-aware backups; disk snapshots alone are not a tested database recovery procedure.

Google login needs GOOGLE_CLIENT_ID and a rotated GOOGLE_CLIENT_SECRET set on the Render service Environment page. Register the final public origin plus /api/v1/auth/google/callback in Google Cloud. RENDER_EXTERNAL_URL determines the correct allowed origin and callback at runtime. Password login is available without Google credentials.

Deploy from render.yaml only after approving its recurring costs. Automatic deploys are disabled. Verify signup, login, owned report access, an image, PDF/OCR, QR, a URL, history, PDF export, deletion and logout on the public URL before announcing readiness. The Docker build and live checks must pass; local unit tests alone do not verify deployment.
