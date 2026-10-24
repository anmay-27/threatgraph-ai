# Security and privacy model

This is a defensive local research tool. It never executes downloaded programs or page JavaScript, probes for vulnerabilities, or uploads private file bytes to third-party services.

URL fetching permits HTTP(S), ports 80/443, and public unicast DNS/IP destinations only. Local/private/link-local/reserved/IPv4-mapped/transition destinations are blocked. All DNS answers are checked and pinned inside the HTTP connector; proxy environment variables are ignored. Redirects are checked again. Limits: 5 redirect hops, 5s connection, 15s per request, 35s fetch-chain deadline, 10 MB response, 25 MB total recursively downloaded bytes, configured recursion depth and asset cap. Encoded HTTP response bodies are rejected to prevent decompression bombs. TLS certificates remain verified.

Uploads use generated storage names and byte-based MIME detection; client names are display-only. Archives are inventoried without extraction or execution. Suspicious member paths and extreme expansion ratios are flagged. Images have a pixel cap; PDF renders and video frame counts are bounded; media duration is capped at 10 minutes. Decoder processes are resource-bounded by Docker, but native codec isolation is not equivalent to a hardened sandbox. Treat hostile files accordingly.

Untrusted text is rendered as React text, never inserted as HTML. Generic files/HTML cannot be previewed. No active link to a discovered malicious target is required to inspect it. API/database errors do not include secrets. SQLAlchemy parameterizes filters. Secrets use environment variables; model files are operator-trusted artifacts only. Never install an untrusted joblib file.

`PRIVACY_MODE=true` overrides external reputation configuration: no URL reputation query is sent. Submitted URLs necessarily contact their destination under the guarded fetcher. C2PA remote-manifest fetching is disabled. Missing credentials are neutral; signature integrity, signer trust and content truth are distinct.

`ENABLE_EXTERNAL_REPUTATION=true`, `PRIVACY_MODE=false`, and an URLhaus Auth-Key opt into sending URL strings to URLhaus. No file payload is sent. This leaks the submitted URL, including query parameters, to that provider; use it only when suitable.

Original uploads expire after RETENTION_HOURS via Celery beat cleanup. Hashes, text excerpts, URLs, EXIF and evidence remain in the local database: these can still be sensitive. The tool does not promise anonymized metadata or encrypted storage. Deploy on an encrypted disk and apply your own metadata retention policy.

Known deployment limits: no authentication/authorization or tenant isolation; local process rate limiting is not distributed; no global durable storage quota; no whole-investigation hard deadline in thread-based development mode; no security certification. Docker binds frontend/API to loopback and does not expose Redis/PostgreSQL. For shared deployment add an authenticated gateway, TLS, CSRF/origin policy, distributed request/job quotas, network egress policy and encrypted backups first.
