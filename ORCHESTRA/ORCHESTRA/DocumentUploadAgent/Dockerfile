FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly install headless opencv
RUN pip install opencv-python-headless

COPY . .

EXPOSE 8000

# Explicitly mapping port 8002 local to 8000 in Docker
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]