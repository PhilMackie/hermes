# Hermes CRM

Personal CRM — part of the quanta/chronos/athena app family.

**Stack:** Python 3 + Flask 3 + SQLite + Jinja2 + PWA
**Port:** 5003
**Theme:** Black + gold (`#f0a500`)
**Favicon:** 8-bit pixel art caduceus

---

## Quick Start

```bash
cd /home/phil/Dev/Claude/hermes
python3 app.py
# → http://localhost:5003
```

Default PIN: `123456` — change `PIN_HASH` in `.env` for production.

---

## Features

### Leads View (`/`)
- Searchable, filterable table of all 113 contacts
- Filter by **tag chips** (multi-select, OR logic), **Working As** dropdown, and **Source** dropdown
- Drag-to-reorder rows (Sortable.js)
- Click any row → Athena-style **slide-in detail panel** (wide, multi-column layout)
- Panel: edit all fields inline, log interactions, view history
- **Bulk actions** via checkboxes: set tag, set working as, delete

### Call Mode (`/call`)
- One contact at a time, ordered by next follow-up date
- Filter by **Working As** + multiple **tag chips** (OR logic, persisted in sessionStorage)
- Actions: **Log** interaction, **Defer** to new date, **Skip** (pushes to tomorrow)

### Settings (`/settings`)
- Tag manager: create / delete tags
- Working As manager: your companies (philmackie.com, PTMP, etc.)
- Source manager: create / delete lead source options (Referral, LinkedIn, etc.)
- CSV export: download all contacts

### Import (`/import`)
- Re-import from bundled Mimiran CSV export

---

## Commands

```bash
# Run dev server
python3 app.py

# Import contacts from Mimiran CSV
python3 scripts/import_mimiran.py

# Generate a new PIN hash
python3 -c "from daemons.auth import hash_pin; print(hash_pin('YOUR_PIN'))"
```

---

## File Structure

```
app.py                    All routes
config.py                 Paths, auth config, PORT=5003
.env                      SECRET_KEY, PIN_HASH (gitignored)
daemons/
  auth.py                 PIN auth + rate limiting + SSO
  contacts.py             DB connection, schema init, all contact ops
  companies.py            Company lookup/create
  interactions.py         Interaction log ops
  settings_daemon.py      Tags + working_as_options + sources
  importer.py             Mimiran CSV import
templates/
  base.html               Nav shell (Leads / Call / Settings)
  login.html              PIN keypad
  leads.html              Table + bulk select + slide-in panel
  call.html               Call mode with filters
  settings.html           Tag + working as managers, CSV export
  import.html             Import trigger UI
static/
  css/style.css           Black + gold theme
  icons/hermes.svg        Caduceus pixel art favicon
  js/app.js               SW registration + utils
  sw.js                   Service worker (PWA)
  manifest.json           PWA manifest
scripts/
  import_mimiran.py       CLI import script
deploy/
  hermes.service          systemd unit (Pi)
  gunicorn.conf.py        Gunicorn config (port 5003)
data/
  hermes.db               SQLite database (gitignored)
```

---

## Auth & SSO

PIN + SHA256. Shares the `network_auth` cookie with quanta/chronos/athena — log in once, access all apps. SSO tokens issued as `{"sso": "hermes"}`.

---

## Deploy (Pi)

```bash
# First time — on Pi:
bash deploy/pi-initial-setup.sh

# From dev machine:
cd deploy
./deploy-to-pi.sh pi@duobrain.local

# On Pi:
bash /opt/hermes/app/deploy/pi-post-transfer.sh

# Future updates (from dev machine):
./deploy-to-pi.sh pi@duobrain.local && ssh pi@duobrain.local "sudo systemctl restart hermes"
```

Pi runs at: `http://192.168.1.71:5003` (duobrain.local)
