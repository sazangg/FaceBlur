Face Blur Service

Overview
This project blurs faces in images, exposes a FastAPI backend with Taskiq + RabbitMQ/Redis for background processing, and includes a React + Vite frontend. A Streamlit demo app lives in `demo/` for quick testing. The backend is organized in a simple layered structure (API, services, workers, storage).

Project layout
- `face_blur/`: backend code (API, services, workers, storage).
- `frontend/`: React + Vite frontend (Tailwind v4 + shadcn/ui).
- `demo/`: Streamlit demo app.

Quality checks
- `ruff check .`
- `black --check .`
- `mypy .`
- `pytest`

Using uv
- Install dependencies: `uv sync --extra dev`
- Run tests: `uv run --extra dev pytest`

Community
- `CONTRIBUTING.md` includes setup and contribution guidelines.
- `LICENSE` is MIT.

Requirements
- Python 3.13+
- Docker Desktop (for RabbitMQ and Redis)

Configuration
Copy `.env.example` to `.env` and set the environment variables:
- `RABBITMQ_URL`: Connection string for RabbitMQ.
- `REDIS_URL`: Connection string for Redis (result backend).
- `BACKEND_URL`: Base URL for the FastAPI service (used by Streamlit).
- `STORAGE_DIR`: Directory where processed images are written before download.
- `ALLOWED_EXTENSIONS`: Comma-separated list of accepted image extensions.
- `MAX_UPLOAD_MB`: Maximum size per uploaded file (defaults to 25).
- `BLUR_RATE_LIMIT`: Rate limit string for the blur endpoint (e.g. `10/minute`).
- `STORAGE_TTL_MINUTES`: Age threshold for background cleanup of stored files.
- `STORAGE_CLEANUP_INTERVAL_MINUTES`: How often the background cleanup runs (set to 0 to disable).
- `LOG_LEVEL`: Logging level (e.g. `INFO`).
- `STATS_DB_PATH`: SQLite file used for vanity stats (e.g. `storage/stats.db`).
- `VISITOR_COOKIE_NAME`: Cookie name used to identify repeat visitors.
- `VISITOR_COOKIE_MAX_AGE_DAYS`: Cookie max age in days.
- `CORS_ALLOW_ORIGINS`: Comma-separated list of allowed frontend origins.

Where to get connection strings
- Local via Docker Compose (recommended for dev): run `docker compose up -d` to start RabbitMQ and Redis, then use:
  - `RABBITMQ_URL=amqp://guest:guest@localhost:5672/`
  - `REDIS_URL=redis://localhost:6379/0`
- Remote services: use the connection strings from your provider dashboards (e.g., CloudAMQP for RabbitMQ or Redis Cloud/Upstash for Redis).

Run dependencies (RabbitMQ + Redis)
```
docker compose up -d
```

Monitoring (Prometheus + Grafana)
```
docker compose up -d prometheus grafana
```

Prometheus will scrape `http://localhost:8000/metrics` via `host.docker.internal`.
Grafana is available at `http://localhost:3000` (admin/admin).
Grafana auto-provisions the Prometheus data source.
Import the dashboard in `monitoring/grafana-dashboard.json`.

Run the API
```
uvicorn face_blur.api.app:app --reload
```

Run the Taskiq worker
```
taskiq worker face_blur.workers.taskiq_app:broker
```

Run the Streamlit app
```
streamlit run demo/streamlit_app.py
```

Run the React app
```
cd frontend
pnpm install
pnpm dev
```

Note
- Run commands from the repository root so `STORAGE_DIR` resolves consistently for both the API and worker.

API Endpoints
- `GET /health`: health check for the backend.
- `POST /blur`: upload one or more images (multipart form field `files`).
- `GET /results/{task_id}`: poll for results; returns image or zip, or 202 while pending.
- `GET /metrics`: Prometheus metrics endpoint.
- `GET /stats`: vanity stats from SQLite.

Response format
- Success payloads return `{ "status": "...", "message": "...", "data": { ... } }`.
- Error payloads return `{ "status": "error", "code": "...", "message": "...", "details": { ... } }`.

Vanity stats
- Visitor counting uses a cookie id; deleting cookies may reduce accuracy.
- `total_requests` tracks blur requests (`POST /blur`), not every endpoint call.

Cleanup behavior
- Processed images are written to `STORAGE_DIR` by the worker and deleted after they are returned by `/results/{task_id}`.
- A background cleanup loop removes files older than `STORAGE_TTL_MINUTES`.
