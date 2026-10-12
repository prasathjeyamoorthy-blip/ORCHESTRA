FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and pdf2image (poppler)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Also copy supabase_db from sibling ORCHESTRA service into this image
# so the sys.path hack is not needed in production
COPY ../ORCHESTRA/supabase_db.py ./supabase_db.py

# Use PORT env var (AWS App Runner / ECS inject this)
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
