# Windsurf World Tour Stats API - Quick Start

**Production URL**: https://windsurf-world-tour-stats-api.duckdns.org
**Status**: ✅ Live
**Last Updated**: 2025-11-07

---

## 🚀 Quick Links

- **API Base**: https://windsurf-world-tour-stats-api.duckdns.org
- **Interactive Docs**: https://windsurf-world-tour-stats-api.duckdns.org/docs
- **Health Check**: https://windsurf-world-tour-stats-api.duckdns.org/health

---

## 📋 Essential Commands

### Access VM
```bash
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
```

### Service Control
```bash
sudo systemctl restart windsurf-api    # Restart service
sudo systemctl status windsurf-api     # Check status
sudo journalctl -u windsurf-api -f     # View live logs
```

### Test API
```bash
curl https://windsurf-world-tour-stats-api.duckdns.org/health
curl https://windsurf-world-tour-stats-api.duckdns.org/api/v1/events?year=2025
```

---

## 🔧 Quick Deploy (After Code Changes)

From your local Git Bash:
```bash
cd "/c/Users/jackf/OneDrive/Documents/Projects/Windsurf World Tour Stats"

# Copy updated file(s)
scp -i ~/.ssh/ssh-key-2025-08-30.key src/api/routes/new_file.py ubuntu@129.151.153.128:/opt/windsurf-api/src/api/routes/

# Restart service
ssh -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128
sudo systemctl restart windsurf-api
```

---

## 📊 Current Endpoints

### GET /health
Health check and status

### GET /api/v1/events
List all windsurf events with filters:
- `?year=2025` - Filter by year
- `?stars=5` - Filter by star rating
- `?country_code=US` - Filter by country
- `?page=1&page_size=50` - Pagination

### GET /api/v1/events/{id}
Get specific event by database ID

---

## 🗄️ Database Info

- **Host**: 10.0.151.92 (Oracle MySQL Heatwave)
- **Database**: jfa_heatwave_db
- **Total Records**: 6,996
- **Tables**: Events, Results, Heat Progression, Heat Results, Heat Scores

---

## 🔍 Troubleshooting

### Service not running?
```bash
sudo journalctl -u windsurf-api -n 50 --no-pager
```

### HTTPS not working?
Check Oracle Cloud Security List has port 443 open

### Database connection issues?
Verify `.env.production` credentials

---

## 📚 Full Documentation

See **DEPLOYMENT.md** for complete setup guide, troubleshooting, and detailed instructions.

---

## 🎯 Next Steps

1. Add more endpoints (results, heats, scores)
2. Restrict CORS to your frontend domain
3. Get custom domain when ready
4. Build your web app!

---

**Quick Reference Card - Keep This Handy!**
