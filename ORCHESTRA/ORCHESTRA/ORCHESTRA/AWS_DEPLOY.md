# AWS Deployment Guide — EC2 + Amplify

## Architecture
```
EC2 Instance (Mumbai: ap-south-1)
  ├── Docker container: ORCHESTRA backend      → port 8001
  └── Docker container: DocumentUploadAgent   → port 8000

AWS Amplify
  └── Frontend (React + Vite)                 → https://*.amplifyapp.com
```

---

## Part 1: EC2 Setup

### 1.1 Launch EC2 Instance
- **AMI:** Ubuntu 22.04 LTS
- **Instance type:** `t3.medium` (2 vCPU, 4GB RAM) — minimum for Playwright
- **Region:** `ap-south-1` (Mumbai)
- **Storage:** 20GB gp3
- **Security Group inbound rules:**
  ```
  Port 22   — SSH (your IP only)
  Port 8000 — DocumentUploadAgent (anywhere or frontend IP)
  Port 8001 — ORCHESTRA backend (anywhere or frontend IP)
  ```

### 1.2 SSH into EC2 and Run Deploy Script
```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Download and run deploy script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/ORCHESTRA/deploy.sh | bash
```

### 1.3 Fill in environment variables
```bash
cd ~/app/ORCHESTRA
nano .env   # fill in all values from .env.example
```

### 1.4 Start the services
```bash
docker compose up -d --build
```

### 1.5 Verify both services are running
```bash
curl http://localhost:8001/   # → {"status":"online","service":"ORCHESTRA Backend Agent"}
curl http://localhost:8000/   # → {"status":"online","service":"Document Upload Agent"}
```

---

## Part 2: AWS Amplify (Frontend)

### 2.1 Go to AWS Amplify Console
- Region: `ap-south-1`
- New App → Host Web App → Connect GitHub

### 2.2 Build Settings
- **Root directory:** `ORCHESTRA/frontend`
- Amplify auto-detects `amplify.yml` in the frontend folder

### 2.3 Set Environment Variables in Amplify Console
```
VITE_API_BASE      = http://<EC2_PUBLIC_IP>:8001
VITE_DOC_API_BASE  = http://<EC2_PUBLIC_IP>:8000
VITE_WS_BASE       = ws://<EC2_PUBLIC_IP>:8001
```
> If you set up a domain with HTTPS, use `https://` and `wss://` instead.

### 2.4 Update ALLOWED_ORIGINS on EC2
After Amplify gives you the URL (`https://xxxxx.amplifyapp.com`):
```bash
# Edit .env on EC2
nano ~/app/ORCHESTRA/.env
# Set: ALLOWED_ORIGINS=https://xxxxx.amplifyapp.com,http://localhost:5173

# Restart containers to pick up the new env var
docker compose down && docker compose up -d
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
git pull && docker compose up -d --build

# Check container status
docker compose ps
```

---

## EC2 Free Tier Note
AWS Free Tier gives you **750 hours/month** of `t2.micro` (1 vCPU, 1GB RAM).
`t2.micro` is too small for Playwright + both backends.
Use `t3.medium` — costs ~$0.04/hour (~₹100/day).
