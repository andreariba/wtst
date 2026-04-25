FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files and install (layer-cached)
COPY ../pyproject.toml ../uv.lock ./
RUN uv sync --frozen --no-dev

COPY monitor.py .

CMD ["uv", "run", "python", "-u", "monitor.py"]