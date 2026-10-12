FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

# Use PORT env var (AWS App Runner / ECS inject this)
EXPOSE 8001

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
