# Quick Start Guide - Windsurf World Tour Stats API

Get the FastAPI application running locally in 5 minutes!

## Prerequisites

- Python 3.11+
- SSH access to Oracle Cloud VM
- Database credentials

## Local Development Setup

### 1. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### 2. Start SSH Tunnel to Database

```bash
# Open a new terminal and run:
ssh -L 3306:10.0.151.92:3306 ubuntu@YOUR_VM_IP

# Keep this terminal open while developing
```

### 3. Configure Environment

Your existing `.env` file should work. Verify it has:
```bash
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=admin
DB_PASSWORD=your_password
```

### 4. Start the API Server

```bash
# From project root directory
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Test the API

Open your browser or use curl:

**Root Endpoint:**
```bash
curl http://localhost:8000/
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

**List Events:**
```bash
curl http://localhost:8000/api/v1/events
```

**Interactive API Docs:**
- Open browser: http://localhost:8000/docs
- Try out endpoints directly in the browser!

## Example API Calls

### Get All Events
```bash
curl http://localhost:8000/api/v1/events
```

### Filter by Year
```bash
curl http://localhost:8000/api/v1/events?year=2025
```

### Filter by Country
```bash
curl http://localhost:8000/api/v1/events?country_code=CL
```

### Filter by Star Rating
```bash
curl http://localhost:8000/api/v1/events?stars=5
```

### Pagination
```bash
curl http://localhost:8000/api/v1/events?page=1&page_size=20
```

### Get Specific Event
```bash
curl http://localhost:8000/api/v1/events/1
```

## API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI** (recommended): http://localhost:8000/docs
- **ReDoc** (alternative): http://localhost:8000/redoc

You can test all endpoints directly in the browser!

## Common Issues

### "Can't connect to MySQL server on 'localhost:3306'"

**Solution:** Start the SSH tunnel first:
```bash
ssh -L 3306:10.0.151.92:3306 ubuntu@YOUR_VM_IP
```

### "ModuleNotFoundError: No module named 'fastapi'"

**Solution:** Install API dependencies:
```bash
pip install -r requirements-api.txt
```

### Port 8000 already in use

**Solution:** Use a different port:
```bash
uvicorn src.api.main:app --reload --port 8001
```

## Next Steps

Once local development is working:

1. **Deploy to Production**: See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment guide
2. **Add More Endpoints**: Edit `src/api/routes/` to add new endpoints
3. **Frontend Integration**: Use the API with your web application

## Production Deployment (Quick Overview)

1. **Copy files to VM:**
   ```bash
   scp -r . ubuntu@YOUR_VM_IP:/opt/windsurf-api/
   ```

2. **Run setup script on VM:**
   ```bash
   ssh ubuntu@YOUR_VM_IP
   cd /opt/windsurf-api
   bash deployment/scripts/setup_vm.sh
   ```

3. **Create .env.production and start service:**
   ```bash
   cp .env.production.template .env.production
   # Edit .env.production with production values
   sudo systemctl start windsurf-api
   ```

4. **Test:**
   ```bash
   curl http://YOUR_VM_IP/health
   ```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## File Structure

```
Windsurf World Tour Stats/
├── src/api/                    # FastAPI application
│   ├── main.py                 # App entry point
│   ├── config.py               # Configuration
│   ├── database.py             # Database connection
│   ├── models.py               # Pydantic models
│   └── routes/
│       └── events.py           # Events endpoints
├── deployment/                 # Deployment configs
│   ├── nginx.conf              # Nginx configuration
│   ├── gunicorn.conf.py        # Gunicorn configuration
│   ├── systemd/                # Systemd service
│   └── scripts/                # Deployment scripts
├── requirements.txt            # Base dependencies
├── requirements-api.txt        # API dependencies
├── .env                        # Local environment (git-ignored)
├── .env.production.template    # Production template
├── QUICKSTART.md              # This file
└── DEPLOYMENT.md              # Full deployment guide
```

## Support

If you encounter issues:
1. Check logs: `sudo journalctl -u windsurf-api -f` (production)
2. Verify environment variables in `.env`
3. Ensure SSH tunnel is running (local dev)
4. See [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section

---

**Happy coding!** 🚀
