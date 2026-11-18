FROM python:3.12-slim

RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean

RUN python -m pip install --upgrade pip && \
    pip install poetry


RUN poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry lock

RUN poetry install --no-root --only main

WORKDIR /app

COPY ./src ./src