#!/bin/bash
# Deployment script for Windsurf World Tour Stats API
# Run this script to deploy code updates to the Oracle VM
#
# Usage: bash deploy.sh [--no-restart]

set -e  # Exit on error

# Variables
APP_DIR="/opt/windsurf-api"
VENV_PATH="$APP_DIR/venv"
SERVICE_NAME="windsurf-api"
RESTART=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-restart)
            RESTART=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash deploy.sh [--no-restart]"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "Windsurf API - Deployment Script"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "src/api/main.py" ]; then
    echo "ERROR: Must run from project root directory"
    exit 1
fi

echo "Step 1: Install/update Python dependencies"
$VENV_PATH/bin/pip install --upgrade pip
$VENV_PATH/bin/pip install -r requirements.txt
$VENV_PATH/bin/pip install -r requirements-api.txt

echo ""
echo "Step 2: Copy application files"
# Copy source code
rsync -av --delete src/ $APP_DIR/src/

# Copy deployment configs
rsync -av deployment/ $APP_DIR/deployment/

# Copy requirements
cp requirements.txt $APP_DIR/
cp requirements-api.txt $APP_DIR/

echo ""
echo "Step 3: Update nginx configuration"
sudo cp $APP_DIR/deployment/nginx.conf /etc/nginx/sites-available/windsurf-api
sudo nginx -t  # Test configuration

echo ""
echo "Step 4: Reload nginx"
sudo systemctl reload nginx

if [ "$RESTART" = true ]; then
    echo ""
    echo "Step 5: Restart API service"
    sudo systemctl restart $SERVICE_NAME

    echo ""
    echo "Step 6: Check service status"
    sleep 2  # Give service time to start
    sudo systemctl status $SERVICE_NAME --no-pager
else
    echo ""
    echo "Skipping service restart (--no-restart flag)"
    echo "Remember to restart manually: sudo systemctl restart $SERVICE_NAME"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Useful commands:"
echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  Service status:   sudo systemctl status $SERVICE_NAME"
echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "  Test API:         curl http://localhost/health"
echo ""
