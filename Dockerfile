FROM python:3.11-slim

WORKDIR /app

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8085

CMD ["python", "server.py"]
