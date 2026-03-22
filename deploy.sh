#!/bin/bash
set -euo pipefail

# Invoice Manager - AWS Deploy Script
# Usage: ./deploy.sh

APP_HOST="18.194.246.133"
SSH_KEY="invoice-portal-key"
DOMAIN="invoice.rhcdemoaccount2.com"

echo "=== Invoice Manager Deploy ==="

# 1. Find SSH key
KEY_PATH=""
for p in "$HOME/.ssh/${SSH_KEY}.pem" "$HOME/.ssh/${SSH_KEY}" "$HOME/${SSH_KEY}.pem"; do
    if [ -f "$p" ]; then KEY_PATH="$p"; break; fi
done
if [ -z "$KEY_PATH" ]; then
    echo "ERROR: SSH key '${SSH_KEY}' not found. Place it in ~/.ssh/${SSH_KEY}.pem"
    exit 1
fi
echo "Using SSH key: $KEY_PATH"

SSH_CMD="ssh -i $KEY_PATH -o StrictHostKeyChecking=no ec2-user@$APP_HOST"
SCP_CMD="scp -i $KEY_PATH -o StrictHostKeyChecking=no"

# 2. Install Docker on the instance
echo "=== Installing Docker & Docker Compose ==="
$SSH_CMD << 'REMOTE'
set -e
if ! command -v docker &> /dev/null; then
    sudo dnf update -y
    sudo dnf install -y docker git
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker ec2-user
fi
# Docker Compose plugin
if ! docker compose version &> /dev/null; then
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi
docker compose version
mkdir -p ~/invoice-manager
REMOTE

# 3. Sync project files
echo "=== Syncing project files ==="
rsync -avz --delete \
    -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude 'dist' \
    --exclude 'backend/data' \
    --exclude '.env' \
    --exclude 'nginx/certbot' \
    ./ ec2-user@$APP_HOST:~/invoice-manager/

# 4. Copy prod env
echo "=== Setting up environment ==="
$SCP_CMD .env.prod ec2-user@$APP_HOST:~/invoice-manager/.env

# 5. Build and start
echo "=== Building and starting services ==="
$SSH_CMD << 'REMOTE'
set -e
cd ~/invoice-manager
# Use newgrp to pick up docker group (in case we just added it)
sg docker -c "docker compose -f docker-compose.prod.yml --env-file .env up -d --build"
echo ""
echo "=== Waiting for services... ==="
sleep 10
sg docker -c "docker compose -f docker-compose.prod.yml ps"
REMOTE

echo ""
echo "=== Deploy complete! ==="
echo "HTTP:  http://$APP_HOST"
echo "HTTP:  http://$DOMAIN (once DNS propagates)"
echo ""
echo "Next steps:"
echo "1. Set up SSL: ssh to instance and run:"
echo "   cd ~/invoice-manager"
echo "   docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot -d $DOMAIN -d rhcdemoaccount2.com"
echo "2. Uncomment HTTPS block in nginx/default.conf"
echo "3. docker compose -f docker-compose.prod.yml restart nginx"
echo "4. Start GPU instance for Ollama: aws ec2 start-instances --instance-ids i-0c51ff7bb68200543"
