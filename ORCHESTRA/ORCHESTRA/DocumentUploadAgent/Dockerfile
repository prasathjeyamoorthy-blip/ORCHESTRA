FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements and install (context is ORCHESTRA/ so path is relative to that)
COPY DocumentUploadAgent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy supabase_db from sibling ORCHESTRA service into this image
COPY ORCHESTRA/supabase_db.py ./supabase_db.py

# Copy DocumentUploadAgent application code
COPY DocumentUploadAgent/ .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
