FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend:/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr libgomp1 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt onnxruntime pytesseract c2pa-python requests
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir transformers==4.57.6 safetensors timm==1.0.15 librosa
COPY backend /app/backend
COPY ml /app/ml
COPY scripts /app/scripts
COPY docker/model-manifests /app/docker/model-manifests
RUN python scripts/install_hosted_models.py
COPY --from=frontend /build/dist /app/frontend/dist
RUN useradd -m -u 10001 investigator && mkdir -p /app/storage && chown investigator:investigator /app/storage
USER investigator
EXPOSE 10000
CMD ["python", "scripts/hosted_app.py"]
