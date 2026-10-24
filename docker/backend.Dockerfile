FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend:/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 ffmpeg tesseract-ocr libgomp1 clamav fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt c2pa-python pytesseract
ARG INSTALL_ML=true
RUN if [ "$INSTALL_ML" = "true" ]; then pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir librosa matplotlib; fi
COPY backend /app/backend
COPY scripts/manage_account.py /app/scripts/manage_account.py
RUN if [ "$INSTALL_ML" = "true" ]; then pip install --no-cache-dir --timeout 120 --retries 5 transformers==4.57.6 safetensors timm==1.0.15; fi
COPY ml /app/ml
COPY models/README.md /app/models/README.md
RUN useradd -m -u 10001 investigator && mkdir -p /app/storage && chown -R investigator:investigator /app/storage /app/models
USER investigator
EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
