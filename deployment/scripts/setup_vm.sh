#!/bin/bash
# Setup script for Oracle VM - Windsurf World Tour Stats API
# Run this script once on the Oracle VM to prepare the environment
#
# Usage: bash setup_vm.sh

set -e  # Exit on error

echo "=========================================="
echo "Windsurf API - VM Setup Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root. Run as your regular user."
    exit 1
fi

# Variables
APP_DIR="/opt/windsurf-api"
PYTHON_VERSION="python3.8"
VENV_PATH="$APP_DIR/venv"

echo "Step 1: Update system packages"
sudo apt update
sudo apt upgrade -y

echo ""
echo "Step 2: Install dependencies"
sudo apt install -y \
    python3.8 \
    python3.8-venv \
    python3.8-dev \
    python3-pip \
    nginx \
    git \
    curl \
    iptables-persistent

echo ""
echo "Step 3: Create application directory"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

echo ""
echo "Step 4: Create log directories"
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn
sudo chown $USER:$USER /var/log/gunicorn
sudo chown $USER:$USER /var/run/gunicorn

echo ""
echo "Step 5: Create Python virtual environment"
$PYTHON_VERSION -m venv $VENV_PATH

echo ""
echo "Step 6: Upgrade pip in virtual environment"
$VENV_PATH/bin/pip install --upgrade pip

echo ""
echo "Step 7: Install Python packages (API only, skip scrapers)"
# Install only API requirements (skip scrapers that need pandas, selenium, etc.)
if [ ! -f "$APP_DIR/requirements-api.txt" ]; then
    echo "Note: requirements-api.txt not found in $APP_DIR"
    echo "You'll need to copy your project files and run:"
    echo "  $VENV_PATH/bin/pip install -r $APP_DIR/requirements-api.txt"
else
    $VENV_PATH/bin/pip install -r $APP_DIR/requirements-api.txt
fi

echo ""
echo "Step 8: Configure nginx"
sudo cp $APP_DIR/deployment/nginx.conf /etc/nginx/sites-available/windsurf-api
sudo ln -sf /etc/nginx/sites-available/windsurf-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Remove default nginx site

echo ""
echo "Step 9: Test nginx configuration"
sudo nginx -t

echo ""
echo "Step 10: Restart nginx"
sudo systemctl restart nginx
sudo systemctl enable nginx

echo ""
echo "Step 11: Install systemd service"
sudo cp $APP_DIR/deployment/systemd/windsurf-api.service /etc/systemd/system/
sudo systemctl daemon-reload

echo ""
echo "Step 12: Configure firewall (Oracle Cloud)"
echo "Opening ports 80 and 443..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create .env.production file in $APP_DIR with your database credentials:"
echo "   DB_HOST=10.0.151.92"
echo "   DB_PORT=3306"
echo "   DB_NAME=jfa_heatwave_db"
echo "   DB_USER=admin"
echo "   DB_PASSWORD=your_password"
echo "   API_ENV=production"
echo ""
echo "2. Copy your application code to $APP_DIR (if not already done)"
echo ""
echo "3. Start the API service:"
echo "   sudo systemctl start windsurf-api"
echo "   sudo systemctl enable windsurf-api"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status windsurf-api"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u windsurf-api -f"
echo ""
echo "6. Test the API:"
echo "   curl http://localhost/health"
echo "   curl http://$(curl -s ifconfig.me)/health"
echo ""
