FROM python:3.12.2-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install asyncio httpx motor

RUN mkdir -p /tmp && chmod 777 /tmp

COPY . .

EXPOSE 8000

CMD ["python3", "main.py"]

