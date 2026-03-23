#!/bin/bash
# Post-Transfer Setup - Run ON THE PI after files transferred
# Usage: bash pi-post-transfer.sh

set -e

echo "=== Hermes Post-Transfer Setup ==="
echo ""

cd /opt/hermes
source venv/bin/activate

# Install Python dependencies
echo "--- Installing Python dependencies ---"
pip install -r app/requirements.txt
pip install gunicorn

# Create .env if it doesn't exist
if [ ! -f /opt/hermes/app/.env ]; then
    echo ""
    echo "--- Creating .env file ---"
    echo "You need to configure the .env file."
    echo ""

    # Generate PIN hash
    echo "Enter your desired PIN (numbers only):"
    read -s PIN
    PIN_HASH=$(python3 -c "from daemons.auth import hash_pin; print(hash_pin('$PIN'))")

    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > /opt/hermes/app/.env << EOF
SECRET_KEY=$SECRET_KEY
AUTH_ENABLED=true
PIN_HASH=$PIN_HASH
EOF

    chmod 600 /opt/hermes/app/.env
    echo ".env created successfully!"
fi

# Install systemd service
echo ""
echo "--- Installing systemd service ---"
sudo cp /opt/hermes/app/deploy/hermes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hermes
sudo systemctl start hermes

echo ""
echo "--- Checking service status ---"
sleep 2
sudo systemctl status hermes --no-pager

echo ""
echo "=== Application setup complete! ==="
echo ""
echo "Test locally: curl -I http://localhost:5003/login"
echo ""
echo "Next: Set up Cloudflare Tunnel (optional)"
echo "  Run: bash /opt/hermes/app/deploy/pi-cloudflare-setup.sh"
