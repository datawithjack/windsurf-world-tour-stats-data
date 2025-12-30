# Windsurf World Tour Stats API - Production Deployment Guide

Complete guide for deploying the FastAPI application with HTTPS to Oracle Cloud VM.

**Last Updated**: 2025-12-30
**Production URL**: https://windsurf-world-tour-stats-api.duckdns.org
**Status**: ✅ Live and operational (Reliability improvements deployed Dec 2025)

---

## Table of Contents
1. [Quick Reference](#quick-reference)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Initial Setup (One-Time)](#initial-setup-one-time)
5. [Deploying Updates](#deploying-updates)
6. [Local Development](#local-development)
7. [Maintenance & Monitoring](#maintenance--monitoring)
8. [Troubleshooting](#troubleshooting)
9. [SSL/HTTPS Configuration](#sslhttps-configuration)
10. [Switching to Custom Domain](#switching-to-custom-domain)

---

## Quick Reference

### Production URLs
- **API Base**: https://windsurf-world-tour-stats-api.duckdns.org
- **Health Check**: https://windsurf-world-tour-stats-api.duckdns.org/health
- **Interactive Docs**: https://windsurf-world-tour-stats-api.duckdns.org/docs
- **ReDoc**: https://windsurf-world-tour-stats-api.duckdns.org/redoc

### VM Details
- **IP Address**: 129.151.153.128
- **SSH Command**: `ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128`
- **Application Path**: `/opt/windsurf-api`
- **Service Name**: `windsurf-api`

### Quick Commands
```bash
# Restart API
sudo systemctl restart windsurf-api

# View logs
sudo journalctl -u windsurf-api -f

# Check status
sudo systemctl status windsurf-api

# Test API
curl https://windsurf-world-tour-stats-api.duckdns.org/health
```

---

## Architecture Overview

### Production Stack
- **FastAPI**: Python web framework
- **Gunicorn**: WSGI server with Uvicorn workers (5 workers, 120s timeout)
- **Nginx**: Reverse proxy (handles HTTPS, rate limiting)
- **Let's Encrypt**: Free SSL certificates (auto-renewal)
- **DuckDNS**: Free subdomain service
- **Systemd**: Service management (auto-restart, logging)
- **MySQL Heatwave**: Database (Oracle Cloud, 10.0.151.92:3306)
  - **Connection Pool**: 20 connections with retry logic and auto-recycle
- **Python 3.8**: Runtime environment

### Network Flow
```
Internet (HTTPS/443)
    ↓
Nginx (SSL termination, reverse proxy)
    ↓
Gunicorn (localhost:8000, 5 workers)
    ↓
FastAPI Application
    ↓
MySQL Heatwave (10.0.151.92:3306)
```

### File Structure
```
/opt/windsurf-api/
├── src/
│   └── api/
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Configuration management
│       ├── database.py          # Database connection pooling
│       ├── models.py            # Pydantic response models
│       └── routes/
│           └── events.py        # Event endpoints
├── deployment/
│   ├── gunicorn.conf.py         # Gunicorn configuration
│   ├── nginx.conf               # Nginx configuration
│   └── systemd/
│       └── windsurf-api.service # Systemd service file
├── venv/                        # Python virtual environment
├── requirements.txt             # Base dependencies
├── requirements-api.txt         # API-specific dependencies
└── .env.production              # Production environment variables
```

---

## Prerequisites

### Local Machine
- **Git Bash** or WSL (for Windows)
- **SSH key**: `~/.ssh/ssh-key-2025-08-30.key`
- Access to Oracle Cloud Console

### Oracle VM
- **OS**: Ubuntu 20.04 LTS
- **Python**: 3.8+ (3.8.10 currently installed)
- **Ports Open**: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **Firewall**: Oracle Cloud Security List configured
- **Resources**: 1GB RAM minimum, 45GB disk

### Oracle Cloud Security List
**Required Ingress Rules:**
| Port | Protocol | Source CIDR | Description |
|------|----------|-------------|-------------|
| 22   | TCP      | 0.0.0.0/0   | SSH access |
| 80   | TCP      | 0.0.0.0/0   | HTTP (redirects to HTTPS) |
| 443  | TCP      | 0.0.0.0/0   | HTTPS |

---

## Initial Setup (One-Time)

### Step 1: Prepare Local Files

**1.1 Create Production Environment File**

Create `.env.production` in project root:
```bash
# Production Environment Configuration
API_ENV=production
API_TITLE=Windsurf World Tour Stats API
API_VERSION=1.0.0
API_DESCRIPTION=API for PWA and IWT windsurf wave competition data (2016-2025)
API_HOST=0.0.0.0
API_PORT=8000

# CORS Settings
CORS_ENABLED=true
CORS_ORIGINS=["*"]

# Database Connection - Production
DB_HOST=10.0.151.92
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=admin
DB_PASSWORD=YOUR_PASSWORD_HERE

# Database Pool Settings (Optimized Dec 2025)
DB_POOL_NAME=windsurf_pool
DB_POOL_SIZE=20
DB_POOL_RESET_SESSION=true
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true

# Logging
LOG_LEVEL=info

# Pagination
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=500
```

**1.2 Update Python Code for Python 3.8 Compatibility**

Ensure all type hints use `typing` module (not Python 3.9+ syntax):
```python
# ❌ Python 3.9+ syntax (doesn't work on 3.8)
from typing import Literal
CORS_ORIGINS: list[str] = ["*"]
def foo(x: str | None) -> list[int]:
    pass

# ✅ Python 3.8 compatible syntax
from typing import Literal, List, Optional
CORS_ORIGINS: List[str] = ["*"]
def foo(x: Optional[str]) -> List[int]:
    pass
```

Files that needed updates:
- `src/api/config.py`: `list[str]` → `List[str]`
- `src/api/models.py`: `list[Event]` → `List[Event]`
- `src/api/database.py`: `tuple | None` → `Optional[tuple]`

**1.3 Update requirements-api.txt**

Ensure `requirements-api.txt` includes database driver:
```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
gunicorn>=21.2.0
mysql-connector-python>=8.0.33
python-multipart>=0.0.6
```

### Step 2: Copy Files to VM

From Git Bash on Windows:
```bash
cd "/c/Users/jackf/OneDrive/Documents/Projects/Windsurf World Tour Stats"

# Create directory on VM
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128 "sudo mkdir -p /opt/windsurf-api && sudo chown ubuntu:ubuntu /opt/windsurf-api"

# Copy application files
scp -i ~/.ssh/ssh-key-2025-08-30.key -r src ubuntu@129.151.153.128:/opt/windsurf-api/
scp -i ~/.ssh/ssh-key-2025-08-30.key -r deployment ubuntu@129.151.153.128:/opt/windsurf-api/
scp -i ~/.ssh/ssh-key-2025-08-30.key requirements.txt requirements-api.txt ubuntu@129.151.153.128:/opt/windsurf-api/
scp -i ~/.ssh/ssh-key-2025-08-30.key .env.production ubuntu@129.151.153.128:/opt/windsurf-api/
```

### Step 3: VM Setup Script

SSH into VM:
```bash
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
```

**3.1 Fix Line Endings (Windows → Linux)**
```bash
cd /opt/windsurf-api
sudo apt-get update
sudo apt-get install -y dos2unix
dos2unix deployment/scripts/setup_vm.sh
```

**3.2 Update Setup Script for Python 3.8**

The setup script was updated to:
- Use `python3.8` instead of `python3.11` (not available on Ubuntu 20.04)
- Install only `requirements-api.txt` (skip scraper dependencies like pandas, selenium)
- Remove PPA installation steps

**3.3 Run Setup Script**
```bash
cd /opt/windsurf-api
bash deployment/scripts/setup_vm.sh
```

This installs:
- Python 3.8 virtual environment
- All API dependencies
- Nginx reverse proxy
- Systemd service
- Firewall rules

### Step 4: Start the Service

```bash
# Start and enable service
sudo systemctl start windsurf-api
sudo systemctl enable windsurf-api

# Check status
sudo systemctl status windsurf-api

# View logs
sudo journalctl -u windsurf-api -f
```

### Step 5: Configure HTTPS with Let's Encrypt

**5.1 Set Up DuckDNS (Free Subdomain)**

1. Go to https://www.duckdns.org/
2. Sign in (no account needed)
3. Choose subdomain: `windsurf-world-tour-stats-api`
4. Enter IP: `129.151.153.128`
5. Save token: `d4e7f695-fe08-40e4-b3f9-d67287c14072`

**5.2 Update Nginx Configuration**

```bash
# Edit nginx config
sudo nano /etc/nginx/sites-available/windsurf-api

# Find and change:
server_name _;
# To:
server_name windsurf-world-tour-stats-api.duckdns.org;

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

**5.3 Install Certbot and Get Certificate**

```bash
# Install certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d windsurf-world-tour-stats-api.duckdns.org

# Follow prompts:
# - Enter email
# - Agree to terms (Y)
# - Redirect HTTP to HTTPS? Choose 2 (Yes)
```

**5.4 Set Up DuckDNS Auto-Update**

```bash
# Create update script
mkdir -p ~/duckdns
cd ~/duckdns

cat > duck.sh << 'EOF'
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=windsurf-world-tour-stats-api&token=d4e7f695-fe08-40e4-b3f9-d67287c14072&ip=" | curl -k -o ~/duckdns/duck.log -K -
EOF

chmod +x duck.sh
./duck.sh
cat duck.log  # Should show "OK"

# Add to crontab (updates every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -
```

**5.5 Add Port 443 to Oracle Cloud Security List**

1. Oracle Cloud Console → Compute → Instances
2. Click your instance → Primary VNIC → Subnet
3. Security Lists → Default Security List
4. Add Ingress Rules:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port: `443`
   - Description: HTTPS access

**5.6 Verify HTTPS**

```bash
# Test
curl https://windsurf-world-tour-stats-api.duckdns.org/health

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Deploying Updates

When you add new endpoints or make changes:

### Option 1: Quick Update (Individual Files)

```bash
# From local machine (Git Bash)
cd "/c/Users/jackf/OneDrive/Documents/Projects/Windsurf World Tour Stats"

# Copy updated file(s)
scp -i ~/.ssh/ssh-key-2025-08-30.key src/api/routes/new_endpoint.py ubuntu@129.151.153.128:/opt/windsurf-api/src/api/routes/

# SSH into VM and restart
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
sudo systemctl restart windsurf-api
sudo systemctl status windsurf-api
```

### Option 2: Full Deployment (All Files)

```bash
# From local machine
cd "/c/Users/jackf/OneDrive/Documents/Projects/Windsurf World Tour Stats"

# Copy all source files
scp -i ~/.ssh/ssh-key-2025-08-30.key -r src ubuntu@129.151.153.128:/opt/windsurf-api/

# SSH and restart
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
sudo systemctl restart windsurf-api
```

### Option 3: Using Deploy Script (On VM)

```bash
# SSH into VM
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
cd /opt/windsurf-api

# Run deploy script (after copying updated files)
bash deployment/scripts/deploy.sh
```

---

## Local Development

### Setup Local Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows Git Bash: source venv/Scripts/activate

# Install dependencies (API only, skip scrapers)
pip install -r requirements-api.txt
```

### Create Local .env File

Create `.env` in project root (for local development):
```bash
API_ENV=development
API_HOST=0.0.0.0
API_PORT=8000

# Database via SSH tunnel
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=admin
DB_PASSWORD=YOUR_PASSWORD

DB_POOL_SIZE=2
LOG_LEVEL=debug
```

### Start SSH Tunnel to Database

```bash
ssh -L 3306:10.0.151.92:3306 -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
```

### Run Development Server

```bash
# From project root
uvicorn src.api.main:app --reload

# Access at:
# http://localhost:8000/docs
# http://localhost:8000/health
```

---

## Maintenance & Monitoring

### Service Management

```bash
# Start service
sudo systemctl start windsurf-api

# Stop service
sudo systemctl stop windsurf-api

# Restart service
sudo systemctl restart windsurf-api

# Check status
sudo systemctl status windsurf-api

# Enable auto-start on boot
sudo systemctl enable windsurf-api

# Disable auto-start
sudo systemctl disable windsurf-api
```

### Viewing Logs

```bash
# Real-time logs (follow)
sudo journalctl -u windsurf-api -f

# Last 100 lines
sudo journalctl -u windsurf-api -n 100

# Logs since today
sudo journalctl -u windsurf-api --since today

# Logs with priority error and above
sudo journalctl -u windsurf-api -p err

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Gunicorn logs
sudo tail -f /var/log/gunicorn/access.log
sudo tail -f /var/log/gunicorn/error.log
```

### SSL Certificate Renewal

Certificates auto-renew via certbot systemd timer. To manually renew:

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# Check certificate expiry
sudo certbot certificates
```

### Database Connection Test

```bash
cd /opt/windsurf-api
source venv/bin/activate
python3 -c "
import mysql.connector
conn = mysql.connector.connect(
    host='10.0.151.92',
    port=3306,
    database='jfa_heatwave_db',
    user='admin',
    password='YOUR_PASSWORD'
)
print('✅ Database connection successful!')
conn.close()
"
```

### System Resources

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check CPU usage
top

# Check API process resources
ps aux | grep gunicorn
```

---

## Troubleshooting

### Service Won't Start

**Check logs for errors:**
```bash
sudo journalctl -u windsurf-api -n 50 --no-pager
```

**Common issues:**

1. **Python version mismatch** (`unsupported operand type(s) for |`)
   - Issue: Python 3.8 doesn't support `list[str]` or `str | None` syntax
   - Fix: Use `List[str]` and `Optional[str]` from typing module

2. **Missing mysql-connector-python**
   - Issue: `ModuleNotFoundError: No module named 'mysql.connector'`
   - Fix: `source venv/bin/activate && pip install mysql-connector-python`

3. **Database connection error**
   - Issue: Can't connect to MySQL
   - Fix: Check `.env.production` has correct credentials

4. **Port already in use**
   - Issue: Port 8000 already bound
   - Fix: `sudo netstat -tlnp | grep 8000` and kill conflicting process

5. **Recursion error** (`maximum recursion depth exceeded`)
   - Issue: Database initialization calls itself
   - Fix: Update `database.py` to set `_pool_initialized = True` before testing connection

### HTTPS Not Working

**Check nginx is listening:**
```bash
sudo ss -tlnp | grep :443
```

**Check certificate exists:**
```bash
sudo ls -la /etc/letsencrypt/live/
```

**Check firewall:**
```bash
# Local iptables
sudo iptables -L INPUT -n --line-numbers | grep 443

# If REJECT rule is before ACCEPT, move it:
sudo iptables -D INPUT <line_number>
sudo iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

**Check Oracle Cloud Security List:**
- Ensure port 443 ingress rule exists with source `0.0.0.0/0`

### DNS Not Resolving

**Check DuckDNS:**
```bash
# Check DNS resolution
nslookup windsurf-world-tour-stats-api.duckdns.org
# Should return: 129.151.153.128

# Check DuckDNS update script
cat ~/duckdns/duck.log  # Should say "OK"

# Manually update
cd ~/duckdns && ./duck.sh
```

### API Returns 502 Bad Gateway

**Nginx can't reach Gunicorn:**
```bash
# Check if Gunicorn is running
sudo systemctl status windsurf-api

# Check if port 8000 is listening
sudo ss -tlnp | grep :8000

# Check nginx error logs
sudo tail -20 /var/log/nginx/error.log
```

### Database Connection Issues

**Test connection manually:**
```bash
cd /opt/windsurf-api
source venv/bin/activate
python3 -c "
import mysql.connector
conn = mysql.connector.connect(
    host='10.0.151.92',
    port=3306,
    database='jfa_heatwave_db',
    user='admin',
    password='YOUR_PASSWORD'
)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM PWA_IWT_EVENTS')
print(f'Events in database: {cursor.fetchone()[0]}')
conn.close()
"
```

---

## SSL/HTTPS Configuration

### Certificate Details

- **Provider**: Let's Encrypt (free)
- **Certificate Path**: `/etc/letsencrypt/live/windsurf-world-tour-stats-api.duckdns.org/`
- **Renewal**: Automatic via certbot systemd timer
- **Validity**: 90 days (auto-renews at 30 days remaining)

### Nginx SSL Configuration

Certbot automatically configures nginx with:
```nginx
listen 443 ssl;
ssl_certificate /etc/letsencrypt/live/windsurf-world-tour-stats-api.duckdns.org/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/windsurf-world-tour-stats-api.duckdns.org/privkey.pem;
include /etc/letsencrypt/options-ssl-nginx.conf;
ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
```

### HTTP to HTTPS Redirect

Nginx redirects all HTTP traffic to HTTPS:
```nginx
if ($scheme != "https") {
    return 301 https://$host$request_uri;
}
```

---

## Switching to Custom Domain

When you get your own domain (e.g., `api.yourdomain.com`):

### Step 1: Update DNS

Point your domain to VM IP:
```
A Record: api.yourdomain.com → 129.151.153.128
```

### Step 2: Get New Certificate

```bash
# SSH into VM
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128

# Update nginx config
sudo nano /etc/nginx/sites-available/windsurf-api
# Change server_name to: api.yourdomain.com

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# Get new certificate
sudo certbot --nginx -d api.yourdomain.com
```

### Step 3: Update Application (Optional)

If you hardcoded the domain anywhere:
```bash
# Update CORS origins in .env.production if needed
CORS_ORIGINS=["https://yourfrontend.com"]
```

### Step 4: Test

```bash
curl https://api.yourdomain.com/health
```

**Note:** Old DuckDNS domain will continue to work unless you delete it.

---

## Production Checklist

Before going live:

### Security
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Database password is strong and secret
- [ ] `.env.production` is not committed to git
- [ ] CORS origins restricted to your frontend domain (not `*`)
- [ ] SSH key-based authentication (no password login)

### Configuration
- [ ] API_ENV set to `production`
- [ ] LOG_LEVEL set to `info` (not `debug`)
- [ ] Database connection pool sized appropriately (5 workers)
- [ ] Gunicorn workers configured (currently 5)

### Monitoring
- [ ] Service auto-starts on boot (`systemctl enable windsurf-api`)
- [ ] Certificate auto-renewal configured
- [ ] DuckDNS auto-update cron job running
- [ ] Know how to view logs (`journalctl -u windsurf-api -f`)

### Testing
- [ ] Health endpoint returns "healthy" status
- [ ] Events endpoint returns data
- [ ] Interactive docs accessible at `/docs`
- [ ] HTTPS works (padlock icon in browser)
- [ ] HTTP redirects to HTTPS

---

## API Endpoints Reference

### Current Endpoints (v1.0.0)

**Base URL**: `https://windsurf-world-tour-stats-api.duckdns.org`

#### Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "api_version": "1.0.0",
  "database": {
    "status": "healthy",
    "database": "mysql://admin@10.0.151.92:3306/jfa_heatwave_db",
    "environment": "production"
  }
}
```

#### List Events
```
GET /api/v1/events?page=1&page_size=50&year=2025&stars=5
```

Query Parameters:
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 50, max: 500)
- `year` (int): Filter by year (2016-2030)
- `source` (str): Filter by source ("PWA" or "Live Heats")
- `country_code` (str): ISO country code (e.g., "CL", "US")
- `stars` (int): Star rating (4-7)
- `wave_only` (bool): Only wave events (default: true)

Response:
```json
{
  "events": [
    {
      "id": 1,
      "source": "PWA",
      "year": 2025,
      "event_id": 3544,
      "event_name": "Hawaii",
      "country_code": "US",
      "stars": 5,
      ...
    }
  ],
  "pagination": {
    "total": 118,
    "page": 1,
    "page_size": 50,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Get Event by ID
```
GET /api/v1/events/{id}
```

Path Parameters:
- `id` (int): Database primary key

Response: Single event object (same structure as list)

### Future Endpoints (Planned)

- `GET /api/v1/results` - Competition results/rankings
- `GET /api/v1/heats` - Heat progression structure
- `GET /api/v1/heat-results` - Heat-by-heat results
- `GET /api/v1/scores` - Individual wave scores

---

## Database Information

### Connection Details
- **Host**: 10.0.151.92 (Oracle MySQL Heatwave)
- **Port**: 3306
- **Database**: jfa_heatwave_db
- **User**: admin
- **Connection**: Direct (production), SSH tunnel (local dev)

### Tables
1. `PWA_IWT_EVENTS` - 118 events (2016-2025)
2. `PWA_IWT_RESULTS` - 2,052 athlete placements
3. `PWA_IWT_HEAT_PROGRESSION` - 219 heat structures
4. `PWA_IWT_HEAT_RESULTS` - 793 heat results
5. `PWA_IWT_HEAT_SCORES` - 3,814 wave scores

**Total Records**: 6,996

---

## Resources & Links

### Documentation
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Gunicorn Docs**: https://docs.gunicorn.org/
- **Nginx Docs**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/
- **DuckDNS**: https://www.duckdns.org/

### Project Files
- **API Source**: `src/api/`
- **Deployment Configs**: `deployment/`
- **Environment Variables**: `.env.production`
- **Requirements**: `requirements-api.txt`

### Related Documentation
- **Project Plan**: `PROJECT_PLAN.md`
- **Database Schema**: `CLAUDE.md`
- **Main README**: `README.md`

---

## Support & Maintenance

### Regular Tasks
- **Daily**: Monitor logs for errors
- **Weekly**: Check disk space and memory
- **Monthly**: Review and rotate logs if needed
- **Every 3 months**: Review and update dependencies

### Automated Tasks
- ✅ SSL certificate renewal (Let's Encrypt timer)
- ✅ DuckDNS IP update (cron every 5 min)
- ✅ Service auto-start on boot (systemd)

### Emergency Contacts
- **Oracle Cloud Console**: https://cloud.oracle.com
- **VM SSH**: `ubuntu@129.151.153.128`
- **Service Logs**: `sudo journalctl -u windsurf-api -f`

---

**Deployment Complete! 🎉**

Last deployed: 2025-11-07
API Version: 1.0.0
Status: Production-ready with HTTPS
