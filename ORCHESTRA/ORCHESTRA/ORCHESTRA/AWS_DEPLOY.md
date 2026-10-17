# AWS Deployment Guide — EC2 + Amplify

## Architecture
```
EC2 Instance (Mumbai: ap-south-1) — 13.207.224.41 (residence-cert.duckdns.org)
  ├── Nginx reverse proxy (SSL via Let's Encrypt, DuckDNS)
  ├── Docker container: ORCHESTRA backend      → port 8001
  └── Docker container: DocumentUploadAgent   → port 8000

AWS Amplify
  └── Frontend (React + Vite)                 → https://vercel-render-production.d3jgbmm7hml0rf.amplifyapp.com
```

---

## Part 1: EC2 Setup

### 1.1 Launch EC2 Instance
- **AMI:** Ubuntu 22.04 LTS
- **Instance type:** `t3.medium` (2 vCPU, 4GB RAM) — minimum for Playwright
- **Region:** `ap-south-1` (Mumbai)
- **Elastic IP:** `13.207.224.41`
- **Domain:** `residence-cert.duckdns.org`
- **Security Group inbound rules:**
  ```
  Port 22   — SSH
  Port 80   — HTTP (redirects to HTTPS)
  Port 443  — HTTPS (Nginx SSL)
  Port 8000 — DocumentUploadAgent
  Port 8001 — ORCHESTRA backend
  ```

### 1.2 SSH into EC2
```bash
ssh -i residence-cert-key.pem ubuntu@13.207.224.41
```

### 1.3 Deploy and Run
```bash
cd ~/app && git pull origin vercel-render-production
cd ORCHESTRA && docker compose down && docker compose up -d --build
```

### 1.4 Verify Services
```bash
curl http://localhost:8001/   # → {"status":"online","service":"ORCHESTRA Backend Agent"}
curl http://localhost:8000/   # → {"status":"online","service":"Document Upload Agent"}
curl https://residence-cert.duckdns.org/
```

---

## Part 2: AWS Amplify (Frontend)

### 2.1 Build Settings
- **Root directory:** `ORCHESTRA/frontend`
- Build spec uses `ORCHESTRA/frontend/amplify.yml`:
  ```yaml
  version: 1
  frontend:
    phases:
      preBuild:
        commands:
          - npm install
      build:
        commands:
          - npm run build
    artifacts:
      baseDirectory: dist
      files:
        - "**/*"
    cache:
      paths:
        - node_modules/**/*
  ```

### 2.2 Environment Variables (Amplify Console)
```
VITE_API_BASE      = https://residence-cert.duckdns.org
VITE_DOC_API_BASE  = https://residence-cert.duckdns.org
VITE_WS_BASE       = wss://residence-cert.duckdns.org
```

---

## Useful Commands on EC2
```bash
# View live logs
docker compose logs -f

# Restart a specific service
docker compose restart orchestra
docker compose restart document-upload

# Pull latest code and redeploy
cd ~/app && git pull origin vercel-render-production && cd ORCHESTRA && docker compose down && docker compose up -d --build

# Check container status
docker compose ps
```
