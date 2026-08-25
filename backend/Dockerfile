# Build context is the repo root (not backend/) -- the backend wraps
# the `snapshot` engine package that lives in ../src, so both need to
# be in the build context together. See docker-compose.yml.

FROM python:3.12-slim

WORKDIR /app

# Install the Snapshot engine itself first (rarely changes -- good layer caching).
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Then the FastAPI wrapper's own dependencies.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend

ENV PYTHONUNBUFFERED=1
ENV SNAPSHOT_REPO_ROOT=/data/workspace

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
