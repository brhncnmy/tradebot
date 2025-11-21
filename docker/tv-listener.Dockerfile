FROM python:3.11-slim

WORKDIR /app

# Copy entire repo
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include repo root
ENV PYTHONPATH=/app

CMD ["uvicorn", "services.tv_listener.src.main:app", "--host", "0.0.0.0", "--port", "8000"]

