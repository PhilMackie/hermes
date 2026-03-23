# Hermes

## Quick Context
- **Project:** Hermes
- **Purpose:** CRM (Customer Relationship Management)
- **Stack:** Python 3 + Flask 3 + SQLite (raw sqlite3, no ORM) + Jinja2 + PWA
- **Port:** 5003
- **Status:** Built — 113 contacts imported from Mimiran

**Phil's Notes:** `/home/phil/Documents/philVault/Projects/Hermes/phils_notes.md`

## Key Resources
- **Vault:** `/home/phil/Documents/philVault/Projects/Hermes/`

## Quick Start
```bash
project_hermes
# or directly:
cd /home/phil/Dev/Claude/hermes
python3 app.py   # dev server on port 5003
```

## Key Commands
```bash
# Import contacts from Mimiran CSV
python3 scripts/import_mimiran.py

# Generate PIN hash
python3 -c "from daemons.auth import hash_pin; print(hash_pin('YOUR_PIN'))"
```

## File Structure
```
app.py              # All routes
config.py           # Paths, PIN_HASH, SECRET_KEY, PORT=5003
daemons/
  auth.py           # PIN auth + rate limiting
  contacts.py       # get_db(), init_schema(), ContactsDaemon
  companies.py      # CompaniesDaemon
  interactions.py   # InteractionsDaemon
  settings_daemon.py # tags + working_as_options + sources
  campaigns.py      # CampaignsDaemon (kanban board)
  importer.py       # Mimiran CSV import
templates/
  base.html         # 4-tab nav: Leads / Call / Campaigns / Settings
  login.html        # PIN keypad
  leads.html        # Table + slide-in detail panel
  call.html         # Call mode (one contact at a time)
  campaigns.html    # Kanban board (campaigns + steps + contact cards)
  settings.html     # Tag mgr, working_as mgr, sources mgr, CSV export
  import.html       # Import trigger
static/css/style.css  # Black + gold (#f0a500) theme
static/icons/hermes.svg  # 8-bit pixel art favicon
scripts/import_mimiran.py
deploy/
  hermes.service        # systemd unit
  gunicorn.conf.py      # port 5003, 2 workers
  deploy-to-pi.sh       # rsync to Pi (run from dev machine)
  pi-initial-setup.sh   # first-time Pi setup (run on Pi)
  pi-post-transfer.sh   # install deps, .env, systemd (run on Pi)
  pi-cloudflare-setup.sh
  DEPLOY.md
```

## Session Log

### 2026-03-09
**Focus:** Initial full build + UX polish
**Completed:**
- Flask app with PIN auth + SSO (shared network cookie with quanta/chronos/athena)
- SQLite schema: contacts, companies, interactions, tags, working_as_options
- Imported 113 contacts from Mimiran CSV export
- Leads view: searchable/filterable table, Athena-style wide slide-in detail panel (multi-column grid layout), Sortable.js drag reorder
- Working As filter dropdown in Leads toolbar
- Bulk select (checkboxes + select-all): bulk set tag, bulk set working as, bulk delete
- Full contact CRUD via slide-in panel
- Interaction log (call/email/meeting/note/other) in panel, split 2-col with history
- Call mode: one contact at a time ordered by next_conversation date, Log/Defer/Skip actions
- Call mode filters: Working As dropdown + multi-select tag chips (OR logic), persisted in sessionStorage
- Settings: tag manager, working_as manager, CSV export
- Import page (UI trigger for Mimiran CSV import)
- Black + gold (#f0a500) theme
- Favicon: 8-bit pixel art caduceus SVG, used inline in nav + login
- PWA: manifest, service worker, mobile-first
- Deploy: systemd service + gunicorn.conf.py (port 5003)
- Deployed to Pi (pi@duobrain.local / 192.168.1.71:5003)
- Fixed search bug: SQL alias mismatch (`contacts.company_id` → `c.company_id` in shared WHERE clause)
- Full deploy scripts in deploy/ matching duo-brain pattern
**Next:**
- Add Hermes Pi to Tailscale for remote access

### 2026-03-13
**Focus:** Feature requests from phils_notes.md
**Completed:**
- Archive contacts: button in panel, Settings toggle (active/archived/all), CSV export option
- Campaign tab: Kanban board, steps, notes, drag-to-move, bulk add from Leads
- Multi-tag filtering in Leads (chip toggle, OR logic — was single-tag only)
- Source field: managed like tags (Settings + dropdown picker in contact panel)
- Click contact card in Campaign view → full slide-in contact detail panel (edit/save/interactions)
- Tag picker in contact panel: multi-select chips instead of free-text input
- Website field added to contacts (DB migration, panel, CSV export)
- All 7 feature requests completed and deployed to Pi (duobrain.local:5003)

### 2026-03-23
**Focus:** Bug fix + feature requests from phils_notes.md
**Completed:**
- Bug fix: campaign dropdown in leads panel now filters to only campaigns with steps; inline success/error feedback inside panel (no longer hidden behind panel); campaigns board auto-refreshes on bfcache restore
- Date defaults in contact panel: last_conversation defaults to today, next_conversation defaults to +7 days; quick buttons +1d/+7d/+14d/+30d (relative to last conversation date)
- Sticky source & working as: saved to localStorage on Save, auto-filled on contacts with empty fields
- Deployed to Pi (duobrain.local:5003)
