#!/bin/bash
# ─────────────────────────────────────────────────────────────
# EC2 One-time Setup + Deploy Script
# Run on a fresh Ubuntu EC2 instance (t3.medium or larger)
# ─────────────────────────────────────────────────────────────
set -e

echo "=== [1/5] Installing Docker ==="
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "=== [2/5] Cloning repository ==="
# Replace with your actual private repo URL
REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/YOUR_REPO.git}"
git clone "$REPO_URL" app
cd app/ORCHESTRA

echo "=== [3/5] Setting up environment ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠  .env file created from template."
  echo "   Edit it now: nano .env"
  echo "   Then re-run: docker compose up -d --build"
  echo ""
  exit 0
fi

echo "=== [4/5] Building and starting containers ==="
docker compose up -d --build

echo "=== [5/5] Done ==="
echo ""
echo "✓ ORCHESTRA backend:       http://$(curl -s ifconfig.me):8001"
echo "✓ DocumentUpload backend:  http://$(curl -s ifconfig.me):8000"
echo ""
echo "To view logs:   docker compose logs -f"
echo "To restart:     docker compose restart"
echo "To stop:        docker compose down"
