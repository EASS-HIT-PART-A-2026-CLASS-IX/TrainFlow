FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY refresh.py ./

# Default to watching the queue; override the command for one-shot drains.
CMD ["uv", "run", "--no-sync", "python", "refresh.py", "watch"]
