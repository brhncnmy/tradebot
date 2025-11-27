FROM python:3.11-slim

WORKDIR /app

# Copy entire repo
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include repo root and pocketoption-bot directory
ENV PYTHONPATH=/app:/app/telegram/pocketoption-bot

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

