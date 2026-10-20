FROM python:3.12-slim

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY main.py ./main.py
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["sh", "-c", ".venv/bin/alembic upgrade head && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"]
