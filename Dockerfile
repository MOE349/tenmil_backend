FROM python:3.11-slim

# Set working dir
WORKDIR /app

# django setting module
ENV DJANGO_SETTINGS_MODULE=configurations.settings

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Ensure entrypoints are executable
RUN chmod +x entrypoint.sh entrypoint-worker.sh entrypoint-beat.sh

# Expose backend port
EXPOSE 8000

# Run using entrypoint
ENTRYPOINT ["./entrypoint.sh"]
