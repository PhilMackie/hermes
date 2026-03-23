#!/bin/bash
# Cloudflare Tunnel Setup - Run ON THE PI
# Usage: bash pi-cloudflare-setup.sh

set -e

echo "=== Cloudflare Tunnel Setup ==="
echo ""

# Install cloudflared
echo "--- Installing cloudflared ---"
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared -y

echo ""
echo "--- Cloudflared installed! ---"
echo ""
echo "Now you need to manually complete the following steps:"
echo ""
echo "1. Authenticate with Cloudflare:"
echo "   cloudflared tunnel login"
echo "   (This will print a URL - open it in a browser to authorize)"
echo ""
echo "2. Create the tunnel:"
echo "   cloudflared tunnel create hermes"
echo "   (Note the UUID it outputs)"
echo ""
echo "3. Add DNS record (replace yourdomain.com):"
echo "   cloudflared tunnel route dns hermes hermes.yourdomain.com"
echo ""
echo "4. Create config file:"
echo "   nano ~/.cloudflared/config.yml"
echo ""
echo "   Paste this (replace YOUR-TUNNEL-UUID and yourdomain.com):"
echo "   ---"
echo "   tunnel: YOUR-TUNNEL-UUID"
echo "   credentials-file: /home/pi/.cloudflared/YOUR-TUNNEL-UUID.json"
echo ""
echo "   ingress:"
echo "     - hostname: hermes.yourdomain.com"
echo "       service: http://localhost:5003"
echo "     - service: http_status:404"
echo "   ---"
echo ""
echo "5. Install as service and start:"
echo "   sudo cloudflared service install"
echo "   sudo systemctl enable cloudflared"
echo "   sudo systemctl start cloudflared"
echo ""
echo "6. Verify:"
echo "   sudo systemctl status cloudflared"
echo "   Visit https://hermes.yourdomain.com from another device"
