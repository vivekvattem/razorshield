FROM python:3.11-slim
WORKDIR /workspace/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
# Regenerate the versioned deployment artifact deterministically during image build.
RUN python scripts/generate_synthetic_data.py --output-dir /workspace/data/generated/default \
    && python scripts/run_offline_detector.py \
    && python -c "from pathlib import Path; from app.services.artifacts import ArtifactService; artifact = ArtifactService(Path('/workspace/artifacts/generated/offline-hgb-v1')).load(); print('verified artifact', artifact.metadata['model_version'], artifact.metadata['model_checksum'])"
COPY backend/scripts/container_start.sh /usr/local/bin/container_start
RUN chmod +x /usr/local/bin/container_start
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health')"
CMD ["container_start"]
