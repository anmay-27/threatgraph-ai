# Larger uploads and document inspection

The default upload limit is now **250 MB**. The API, example configuration, Docker proxy limit, frontend validation, and local scanner configuration have been updated together. An existing custom `MAX_UPLOAD_MB` setting overrides the default. Remote URL downloads retain their smaller network-fetch budget. Videos still have a ten-minute processing limit.

PDF inspection reads up to 30 pages of text and declared hyperlinks, checks up to 10,000 PDF objects for JavaScript markers, and inventories embedded files. QR inspection covers the first ten pages. Scanned pages can use optional installed Tesseract/pytesseract OCR on the first five pages; unreadable or unprocessed pages are reported explicitly. Encrypted PDFs require an authorized decrypted copy.

Modern Office documents (DOCX, XLSX, PPTX containers) now receive bounded XML text extraction, external relationship inventory, VBA macro and embedded-object checks. No macros, scripts, or embedded files execute. Legacy binary DOC/XLS/PPT formats are not supported by this extractor; export them to PDF or modern Office format first. This does not verify document authorship, a certificate, or factual claims.

Document reports show inspected pages/parts, readable text, links, structural flags, limitations, and next steps. PDF exports include the same extracted-text preview and document findings. Declared hyperlinks are inventoried rather than fetched automatically; existing PDF QR investigation remains separate.

Live validation completed with readable PDF and DOCX uploads and a generated 41,436,900-byte AVI video. All three decoded/parsed and passed local malware signature scanning; both document PDF exports contained the extracted text. The faceless test video's manipulation model abstained because it requires face coverage. This validates larger upload handling, not video-detector accuracy. FFmpeg-dependent audio extraction remains unavailable when FFmpeg is not installed.

Reproduce with `scripts/verify_document_uploads.py`; local evidence is in `research/results/document-upload-check/validation.json`. Start the services with `scripts/start_local.py --browser` first. Run a new analysis after upgrading; historical reports retain their original evidence.
