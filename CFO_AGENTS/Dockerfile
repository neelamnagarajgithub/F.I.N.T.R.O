# Use python slim image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install build deps required by some packages (adjust if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy root requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ensure gunicorn + uvicorn are present (Cloud Run needs the server binaries)
RUN pip install --no-cache-dir gunicorn uvicorn

# Copy repository into container
COPY . /app

# Ensure repo root on PYTHONPATH so imports like CashFlow_Agents work
ENV PYTHONPATH=/app:$PYTHONPATH
# Cloud Run provides PORT; default to 8080
ENV PORT=8080

EXPOSE 8080

# Use Gunicorn + Uvicorn worker for production and expand $PORT at runtime
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker Backend.app:app -b 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300"]