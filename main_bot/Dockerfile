FROM python:3.12.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Инструменты и заголовки для сборки C-расширений
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# (опционально) обновим pip/setuptools/wheel до свежих —
# часто спасает от проблем со сборкой пакетов
RUN python -m pip install --upgrade pip setuptools wheel

# Кэш слоёв: сначала зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

# Потом код
COPY . .

EXPOSE 8000

CMD ["python3", "main.py"]
