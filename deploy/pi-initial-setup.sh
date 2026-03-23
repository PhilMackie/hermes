#!/bin/bash
# Initial Pi Setup Script - Run ON THE PI after first SSH
# Usage: bash pi-initial-setup.sh

set -e

echo "=== Hermes Pi Initial Setup ==="
echo ""

# Phase 2: System Configuration
echo "--- Phase 2: System Update & Config ---"
sudo apt update && sudo apt upgrade -y
sudo raspi-config nonint do_memory_split 16

# Firewall
echo "--- Installing firewall ---"
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw allow ssh
echo "y" | sudo ufw enable

# Phase 3: Python Environment
echo ""
echo "--- Phase 3: Python Environment ---"
sudo apt install python3 python3-pip python3-venv python3-dev libffi-dev libssl-dev -y

# Create app directory structure
echo "--- Creating directory structure ---"
sudo mkdir -p /opt/hermes
sudo chown pi:pi /opt/hermes
mkdir -p /opt/hermes/app
mkdir -p /opt/hermes/logs
mkdir -p /opt/hermes/data

# Create virtual environment
echo "--- Creating Python virtual environment ---"
cd /opt/hermes
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

echo ""
echo "=== Initial setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. From your dev machine, run: ./deploy-to-pi.sh"
echo "  2. Back on Pi, run: bash /opt/hermes/app/deploy/pi-post-transfer.sh"
echo ""
echo "Rebooting in 5 seconds to apply memory split..."
sleep 5
sudo reboot
