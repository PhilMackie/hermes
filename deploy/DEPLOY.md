# Hermes Raspberry Pi Deployment

## Credentials

| Item | Value |
|------|-------|
| Pi Username | `pi` |
| Hostname | `hermes` / `hermes.local` |
| Tailscale | `pi@hermes` |

## Quick Reference

### Phase 1: SD Card Setup (Manual)
1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose: **Raspberry Pi OS (other) → Raspberry Pi OS Lite (Legacy, 32-bit)**
3. Click gear icon, configure:
   - Hostname: `hermes`
   - Enable SSH with password
   - Username: `pi`, set strong password
   - Configure WiFi
   - Set timezone
4. Write to SD card, insert in Pi, power on

### Phase 2-3: Initial Pi Setup
```bash
# From your machine, SSH to Pi
ssh pi@hermes.local

# Run initial setup
bash pi-initial-setup.sh
# Pi will reboot — SSH back in after
```

### Phase 4: Transfer Application
```bash
# From your dev machine (this directory)
cd /home/phil/Dev/Claude/hermes/deploy

./deploy-to-pi.sh
```

### Phase 5-6: Configure & Start Service
```bash
# SSH to Pi
ssh pi@hermes.local

# Run post-transfer setup (installs deps, creates .env, starts service)
bash /opt/hermes/app/deploy/pi-post-transfer.sh
```

### Phase 7: Cloudflare Tunnel (optional)
```bash
# On Pi
bash /opt/hermes/app/deploy/pi-cloudflare-setup.sh
# Follow the printed instructions
```

## Files in this Directory

| File | Purpose | Run Where |
|------|---------|-----------|
| `deploy-to-pi.sh` | Rsync app files to Pi | Dev machine |
| `pi-initial-setup.sh` | System setup, Python, dirs | Pi |
| `pi-post-transfer.sh` | Install deps, create .env, start service | Pi |
| `pi-cloudflare-setup.sh` | Install cloudflared + instructions | Pi |
| `gunicorn.conf.py` | Production server config | Copied to Pi |
| `hermes.service` | Systemd unit file | Installed on Pi |
| `.env.pi` | Example environment config | Reference |
| `cloudflared-config.yml` | Tunnel config template | Reference |

## Useful Commands

```bash
# Check service status
sudo systemctl status hermes
sudo systemctl status cloudflared

# View logs
journalctl -u hermes -f
journalctl -u cloudflared -f
tail -f /opt/hermes/logs/error.log

# Restart after code update
sudo systemctl restart hermes

# Check memory usage
free -h
```

## Future Updates

Just run from dev machine:
```bash
./deploy-to-pi.sh && ssh pi@hermes.local "sudo systemctl restart hermes"
```

Or with Tailscale:
```bash
PI_HOST="pi@hermes" ./deploy-to-pi.sh && ssh pi@hermes "sudo systemctl restart hermes"
```
