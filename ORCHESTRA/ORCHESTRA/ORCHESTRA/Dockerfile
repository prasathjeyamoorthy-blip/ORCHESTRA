FROM python:3.11-slim

WORKDIR /app

# Upgrade pip first to ensure latest wheel resolution
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser and system dependencies
RUN playwright install chromium --with-deps

ENV HEADLESS=true

COPY . .

EXPOSE 8001

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
