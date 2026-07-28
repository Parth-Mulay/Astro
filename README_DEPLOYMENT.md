# AstroMatch Production Deployment Guide

This document describes how to deploy the AstroMatch platform to a production Ubuntu server (e.g., Hetzner VPS) using **Docker & Docker Compose** (Recommended) or as a native **Systemd Service**.

---

## 📋 Prerequisites
1. An Ubuntu 22.04 / 24.04 server (Hetzner Cloud VPS or equivalent).
2. A registered domain name (e.g., `astromatch.com`) pointing to the server's public IP address.
3. Razorpay account details (Key ID, Secret, and Webhook Secret).

---

## 🛡️ Step 1: Server Hardening & Firewall (UFW)
Log into your Ubuntu server as root (or a user with sudo privileges) and run:

```bash
# Update package index
sudo apt update && sudo apt upgrade -y

# Configure Firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh          # Port 22
sudo ufw allow http         # Port 80
sudo ufw allow https        # Port 443
sudo ufw --force enable
```

---

## 🐳 Step 2: Install Docker & Docker Compose
If you choose the Docker deployment method, install the Docker engine:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

---

## 🚀 Step 3: Project Setup & Environment Config
Clone the project repository into `/var/www/astromatch` and set up your configurations:

```bash
sudo mkdir -p /var/www/astromatch
sudo chown -R $USER:www-data /var/www/astromatch
cd /var/www/astromatch

# Create production .env file (copying from .env.example)
cp .env.example .env
```

Open `.env` using your favorite text editor (`nano .env`) and modify the settings:
1. Set `ENVIRONMENT=production`.
2. Change `SESSION_SECRET` to a cryptographically strong hex string:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Set `SECURE_COOKIES=true` (this ensures session cookies are only transmitted over HTTPS).
4. Enter your production `RAZORPAY_KEY_ID`, `RAZORPAY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`.

---

## 🛠️ Method A: Deploying via Docker & Docker Compose (Recommended)

### 1. Build and Start the Containers
Start the containers in detached mode:
```bash
docker compose up -d --build
```
This starts two services:
*   `astromatch_web`: Running the FastAPI application via Gunicorn/Uvicorn on port `8000` internally.
*   `astromatch_nginx`: Running Nginx on ports `80` and `443`.

### 2. Configure Let's Encrypt (SSL Certificates)
Initially, Nginx boots with self-signed dummy SSL certificates (`ssl-cert-snakeoil`). Install Certbot to provision valid Let's Encrypt SSL certificates:

```bash
# Install Certbot on Host
sudo apt install certbot -y

# Obtain SSL Certificate
sudo certbot certonly --webroot -w /var/www/certbot -d yourdomain.com
```

### 3. Update Nginx with Production Certificates
Once Certbot successfully creates the certificates under `/etc/letsencrypt/live/yourdomain.com/`, edit `nginx/nginx.conf`:

```nginx
# Comment out snakeoil lines:
# ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
# ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

# Uncomment and update your Let's Encrypt certificates:
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

Reload Nginx inside Docker to apply:
```bash
docker compose exec nginx nginx -s reload
```

---

## ⚙️ Method B: Native Systemd Deployment (Non-Docker Fallback)

If you prefer to deploy directly on the Ubuntu OS without Docker containers, follow this method:

### 1. Install System Dependencies
Install Python 3.12 (if not default), virtualenv, and Nginx:
```bash
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
```

### 2. Initialize Virtual Environment & Install Packages
```bash
cd /var/www/astromatch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup Systemd Service
Copy the systemd file to the system services directory and enable it:
```bash
sudo cp systemd/astromatch.service /etc/systemd/system/astromatch.service
sudo systemctl daemon-reload
sudo systemctl start astromatch
sudo systemctl enable astromatch
```

### 4. Setup Host Nginx Configuration
Copy the reverse proxy configuration:
```bash
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
# Note: You may need to edit /etc/nginx/nginx.conf to change the upstream server block
# from `web:8000` to `127.0.0.1:8000` for a local host setup.
```

Reload host Nginx and run Certbot to automatically fetch and configure SSL:
```bash
sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 💳 Razorpay Webhook Configuration
To complete wallet recharges asynchronously even if a client closes their browser before redirection:
1. Log into the Razorpay Dashboard.
2. Navigate to **Settings** -> **Webhooks**.
3. Click **Add New Webhook** and configure:
   *   **Webhook URL**: `https://yourdomain.com/payment/razorpay/webhook`
   *   **Secret**: Value matching `RAZORPAY_WEBHOOK_SECRET` in your `.env`.
   *   **Active Events**: Select `payment.captured`.
4. Save the webhook.

---

## 💾 Backups Configuration (SQLite & Uploads)
Automate system backups by creating a cron job. The backup script automatically archives the SQLite database, logs, user uploads, and generated reports, keeping only the 7 most recent backups to optimize disk space.

Make the scripts executable:
```bash
chmod +x scripts/backup.sh scripts/restore.sh scripts/startup.sh
```

To run a backup daily at 2:00 AM, edit the system crontab:
```bash
crontab -e
```
Add the following line to the bottom:
```cron
0 2 * * * cd /var/www/astromatch && ./scripts/backup.sh >> /var/www/astromatch/logs/backup.log 2>&1
```

To manually restore system state from a backup:
```bash
./scripts/restore.sh backups/astromatch_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 🔍 Log Monitoring & Troubleshooting
*   **Docker Container Logs**:
    ```bash
    docker compose logs -f web    # FastAPI backend logs
    docker compose logs -f nginx  # Nginx web server logs
    ```
*   **Systemd Logs**:
    ```bash
    journalctl -u astromatch -f -n 100
    ```
*   **Application Log Files**:
    ```bash
    tail -f logs/application.log   # Application prints and info logs
    tail -f logs/error.log         # Production error traces
    tail -f logs/access.log        # HTTP request logs
    ```
