FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Upgrade pip first to ensure latest wheel resolution
RUN pip install --upgrade pip

# Install dependencies — use only pre-built wheels, never compile from source
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
