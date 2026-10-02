FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8085

EXPOSE 8085

CMD ["python", "server.py"]
