"""
Importer - Mimiran CSV import logic.
"""

import csv
import sqlite3
import config
from daemons.contacts import get_db


MIMIRAN_FIELD_MAP = {
    "Id": "mimiran_id",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Title": "title",
    "Email": "email",
    "Phone": "phone",
    "Mobile Phone": "mobile_phone",
    "Last Conversation": "last_conversation",
    "Next Conversation": "next_conversation",
    "Source URL": "source_url",
    "Source Page": "source_page",
    "Referring Contact": "referring_contact",
    "LinkedIn Profile": "linkedin_profile",
    "Facebook Profile": "facebook_profile",
    "Twitter Profile": "twitter_profile",
    "Calendar Link": "calendar_link",
    "Tags": "tags",
    "Ideal Client": "ideal_client",
    "Ideal Partner": "ideal_partner",
    "Description": "description",
    "Billing Street": "billing_street",
    "Billing City": "billing_city",
    "Billing State": "billing_state",
    "Billing Postal Code": "billing_postal_code",
    "Billing Country": "billing_country",
    "URL": "source_url",
}


def parse_date(val):
    """Convert MM/DD/YYYY to YYYY-MM-DD, return None if blank."""
    if not val or not val.strip():
        return None
    val = val.strip()
    parts = val.split("/")
    if len(parts) == 3:
        m, d, y = parts
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return val


def get_or_create_company_inline(conn, name):
    """Get or create company using existing connection."""
    if not name:
        return None
    row = conn.execute("SELECT id FROM companies WHERE name=?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (name) VALUES (?)", (name,))
    return cur.lastrowid


def import_csv(filepath):
    imported = 0
    skipped = 0
    errors = []

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    for i, row in enumerate(rows):
        try:
            mimiran_id = row.get("Id", "").strip()
            first_name = row.get("First Name", "").strip()

            if not first_name:
                skipped += 1
                continue

            # Company
            company_name = row.get("Company", "").strip()
            company_id = None
            if company_name:
                company_id = get_or_create_company_inline(conn, company_name)

            last_conv = parse_date(row.get("Last Conversation", ""))
            next_conv = parse_date(row.get("Next Conversation", ""))

            ideal_client_val = row.get("Ideal Client", "").strip().lower()
            ideal_client = 1 if ideal_client_val in ("1", "true", "yes", "x") else 0

            ideal_partner_val = row.get("Ideal Partner", "").strip().lower()
            ideal_partner = 1 if ideal_partner_val in ("1", "true", "yes", "x") else 0

            # Check if already exists (by mimiran_id)
            existing = None
            if mimiran_id:
                existing = conn.execute(
                    "SELECT id FROM contacts WHERE mimiran_id=?", (mimiran_id,)
                ).fetchone()

            params = (
                first_name,
                row.get("Last Name", "").strip(),
                row.get("Title", "").strip(),
                row.get("Email", "").strip(),
                row.get("Phone", "").strip(),
                row.get("Mobile Phone", "").strip(),
                company_id,
                row.get("Tags", "").strip(),
                row.get("LinkedIn Profile", "").strip(),
                row.get("Facebook Profile", "").strip(),
                row.get("Twitter Profile", "").strip(),
                row.get("Calendar Link", "").strip(),
                row.get("Source URL", "").strip() or row.get("URL", "").strip(),
                row.get("Source Page", "").strip(),
                row.get("Referring Contact", "").strip(),
                ideal_client,
                ideal_partner,
                row.get("Description", "").strip(),
                row.get("Billing Street", "").strip(),
                row.get("Billing City", "").strip(),
                row.get("Billing State", "").strip(),
                row.get("Billing Postal Code", "").strip(),
                row.get("Billing Country", "").strip(),
                last_conv,
                next_conv,
                i,  # sort_order
            )

            if existing:
                conn.execute(
                    """UPDATE contacts SET
                       first_name=?, last_name=?, title=?, email=?, phone=?, mobile_phone=?,
                       company_id=?, tags=?, linkedin_profile=?, facebook_profile=?, twitter_profile=?,
                       calendar_link=?, source_url=?, source_page=?, referring_contact=?,
                       ideal_client=?, ideal_partner=?, description=?,
                       billing_street=?, billing_city=?, billing_state=?, billing_postal_code=?, billing_country=?,
                       last_conversation=?, next_conversation=?, sort_order=?,
                       updated_at=datetime('now')
                       WHERE mimiran_id=?""",
                    params + (mimiran_id,)
                )
            else:
                conn.execute(
                    """INSERT INTO contacts
                       (first_name, last_name, title, email, phone, mobile_phone,
                        company_id, tags, linkedin_profile, facebook_profile, twitter_profile,
                        calendar_link, source_url, source_page, referring_contact,
                        ideal_client, ideal_partner, description,
                        billing_street, billing_city, billing_state, billing_postal_code, billing_country,
                        last_conversation, next_conversation, sort_order, mimiran_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    params + (int(mimiran_id) if mimiran_id else None,)
                )
            imported += 1

        except Exception as e:
            errors.append(f"Row {i+2}: {e}")

    conn.commit()
    conn.close()

    return {"imported": imported, "skipped": skipped, "errors": errors}
