FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY face_blur ./face_blur
COPY frontend ./frontend
COPY main.py ./

RUN pip install --upgrade pip \
    && pip install .

RUN useradd --create-home appuser \
    && mkdir -p /app/storage \
    && chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "face_blur.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
