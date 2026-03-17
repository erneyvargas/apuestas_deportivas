FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Virtualenv fuera del directorio montado para no pisarlo con permisos root
ENV UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8001

CMD ["uv", "run", "python", "main.py"]
