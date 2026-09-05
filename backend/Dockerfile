FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data \
    HOST=0.0.0.0

RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser \
    && mkdir -p /app/data /app/plugins \
    && chown -R appuser:appuser /app

COPY pyproject.toml ./
COPY app ./app
COPY plugins ./plugins
COPY scripts ./scripts

RUN pip install --upgrade pip \
    && pip install . \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

# 0.0.0.0 داخل الحاوية مطلوب لاستقبال الطلبات من شبكة Docker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
