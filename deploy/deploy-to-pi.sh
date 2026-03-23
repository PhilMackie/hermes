#!/bin/bash
# Deploy Hermes to Raspberry Pi
# Run from: /home/phil/Dev/Claude/hermes/deploy/
# Usage: ./deploy-to-pi.sh [hostname]

set -e

PI_HOST="${1:-pi@hermes.local}"
APP_SRC="/home/phil/Dev/Claude/hermes"
APP_DEST="/opt/hermes/app"

echo "=== Deploying Hermes to $PI_HOST ==="

# Sync app files (excludes sensitive/generated files)
echo "Syncing application files..."
rsync -avz --progress \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'data/' \
  --exclude '.env' \
  --exclude 'credentials/' \
  --exclude 'deploy/' \
  --exclude '.claude/' \
  "$APP_SRC/" \
  "$PI_HOST:$APP_DEST/"

# Sync deployment configs
echo "Syncing deployment configs..."
rsync -avz --progress \
  "$APP_SRC/deploy/gunicorn.conf.py" \
  "$PI_HOST:/opt/hermes/"

# Install/update Python dependencies
echo "Installing dependencies..."
ssh "$PI_HOST" "/opt/hermes/venv/bin/pip install -q -r $APP_DEST/requirements.txt"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Next steps on the Pi:"
echo "  ssh $PI_HOST"
echo "  sudo systemctl restart hermes"
echo "  sudo systemctl status hermes"
