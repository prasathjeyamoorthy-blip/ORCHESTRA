FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN pip install playwright
RUN playwright install --with-deps

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]