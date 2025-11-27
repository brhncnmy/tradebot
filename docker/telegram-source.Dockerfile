FROM python:3.11-slim

WORKDIR /app

# Copy entire repo
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include repo root and telegram-source directory
ENV PYTHONPATH=/app:/app/telegram/telegram-source

CMD ["python", "-m", "app.main"]

