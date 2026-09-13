FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY certs ./certs

RUN pip install --no-cache-dir . \
    && mkdir -p /app/data

VOLUME ["/app/data"]

CMD ["python", "-m", "telegram_dapnet_bot"]
