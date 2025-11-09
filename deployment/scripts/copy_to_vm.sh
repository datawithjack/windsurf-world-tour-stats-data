#!/bin/bash
# Copy project files from local machine to VM
# Run this from your LOCAL MACHINE (not on the VM)

set -e

VM_USER="ubuntu"
VM_HOST="129.151.153.128"
SSH_KEY="$HOME/.ssh/ssh-key-2025-08-30.key"
APP_DIR="/opt/windsurf-api"

echo "=========================================="
echo "Copy Project Files to VM"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -f "src/api/main.py" ]; then
    echo "ERROR: Must run from project root directory"
    exit 1
fi

echo "Step 1: Create application directory on VM"
ssh -i "$SSH_KEY" "$VM_USER@$VM_HOST" "sudo mkdir -p $APP_DIR && sudo chown $VM_USER:$VM_USER $APP_DIR"

echo ""
echo "Step 2: Copy source code"
rsync -avz --delete -e "ssh -i $SSH_KEY" \
    src/ "$VM_USER@$VM_HOST:$APP_DIR/src/"

echo ""
echo "Step 3: Copy deployment files"
rsync -avz -e "ssh -i $SSH_KEY" \
    deployment/ "$VM_USER@$VM_HOST:$APP_DIR/deployment/"

echo ""
echo "Step 4: Copy requirements files"
scp -i "$SSH_KEY" requirements.txt "$VM_USER@$VM_HOST:$APP_DIR/"
scp -i "$SSH_KEY" requirements-api.txt "$VM_USER@$VM_HOST:$APP_DIR/"

echo ""
echo "Step 5: Copy production environment file"
scp -i "$SSH_KEY" .env.production "$VM_USER@$VM_HOST:$APP_DIR/.env.production"

echo ""
echo "=========================================="
echo "Files Copied Successfully!"
echo "=========================================="
echo ""
echo "Next: SSH into VM and run setup script"
echo "  ssh -i $SSH_KEY $VM_USER@$VM_HOST"
echo "  cd $APP_DIR"
echo "  bash deployment/scripts/setup_vm.sh"
echo ""
