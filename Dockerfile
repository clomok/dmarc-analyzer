FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (netcat for wait loop, build tools)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script and make it executable
COPY entrypoint.py .

COPY . .

# Set the entrypoint
ENTRYPOINT ["python", "/app/entrypoint.py"]

# Default command (passed to the 'exec $@' in entrypoint)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]