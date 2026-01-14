FROM python:3.12-slim

# Устанавливаем переменные окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

RUN pip install fastapi uvicorn pydantic aiohttp tonsdk tonutils asyncio

RUN mkdir -p /tmp && chmod 777 /tmp

COPY . .

EXPOSE 8000

CMD ["python3", "app.py"]

