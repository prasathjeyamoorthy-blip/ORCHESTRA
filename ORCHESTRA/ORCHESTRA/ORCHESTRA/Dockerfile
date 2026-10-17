FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Playwright browsers are fully installed
RUN playwright install chromium

COPY . .

EXPOSE 8001

# Mapping port 8000 local to 8001 in Docker
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
