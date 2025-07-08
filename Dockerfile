FROM python:3.11-slim

# Set working dir
WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose backend port
EXPOSE 8000

# Run using entrypoint
ENTRYPOINT ["./entrypoint.sh"]
