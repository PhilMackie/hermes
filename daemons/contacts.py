"""
ContactsDaemon - database access and contact operations.
"""

import sqlite3
import config


def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mimiran_id INTEGER UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT,
            title TEXT,
            email TEXT,
            phone TEXT,
            mobile_phone TEXT,
            company_id INTEGER,
            tags TEXT,
            linkedin_profile TEXT,
            facebook_profile TEXT,
            twitter_profile TEXT,
            calendar_link TEXT,
            source_url TEXT,
            source_page TEXT,
            referring_contact TEXT,
            ideal_client INTEGER DEFAULT 0,
            ideal_partner INTEGER DEFAULT 0,
            description TEXT,
            billing_street TEXT,
            billing_city TEXT,
            billing_state TEXT,
            billing_postal_code TEXT,
            billing_country TEXT,
            last_conversation TEXT,
            next_conversation TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            working_as TEXT,
            sort_order INTEGER DEFAULT 0,
            website TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS working_as_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
    """)
    conn.commit()

    # Migrations for existing DBs
    for col in [("source", "TEXT DEFAULT ''"), ("is_archived", "INTEGER DEFAULT 0"), ("website", "TEXT DEFAULT ''")]:
        try:
            conn.execute(f"ALTER TABLE contacts ADD COLUMN {col[0]} {col[1]}")
            conn.commit()
        except Exception:
            pass  # Column already exists

    conn.close()


def list_contacts(q=None, tags=None, working_as=None, source=None, archived='active', page=1, per_page=50):
    """tags: list of tag names (OR logic), or None for no filter.
    archived: 'active' (default), 'archived', or 'all'."""
    conn = get_db()
    cur = conn.cursor()

    conditions = []
    params = []

    if archived == 'active':
        conditions.append("c.is_archived = 0")
    elif archived == 'archived':
        conditions.append("c.is_archived = 1")

    if q:
        conditions.append(
            "(first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR "
            "(SELECT name FROM companies WHERE id = c.company_id) LIKE ?)"
        )
        like = f"%{q}%"
        params.extend([like, like, like, like])

    if tags:
        tag_clauses = ["(',' || tags || ',' LIKE ?)" for _ in tags]
        conditions.append("(" + " OR ".join(tag_clauses) + ")")
        params.extend(f"%,{t},%" for t in tags)

    if working_as:
        conditions.append("working_as = ?")
        params.append(working_as)

    if source:
        conditions.append("source = ?")
        params.append(source)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_row = cur.execute(
        f"SELECT COUNT(*) FROM contacts c {where}", params
    ).fetchone()
    total = count_row[0]

    offset = (page - 1) * per_page
    rows = cur.execute(
        f"""SELECT c.*, co.name as company_name
            FROM contacts c
            LEFT JOIN companies co ON c.company_id = co.id
            {where}
            ORDER BY c.sort_order ASC, c.id ASC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset]
    ).fetchall()

    conn.close()
    return {
        "contacts": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }


def get_contact(contact_id):
    conn = get_db()
    row = conn.execute(
        """SELECT c.*, co.name as company_name
           FROM contacts c
           LEFT JOIN companies co ON c.company_id = co.id
           WHERE c.id = ?""",
        (contact_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_contact(data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO contacts
           (first_name, last_name, title, email, phone, mobile_phone,
            company_id, tags, linkedin_profile, facebook_profile, twitter_profile,
            calendar_link, source_url, source_page, referring_contact,
            ideal_client, ideal_partner, description,
            billing_street, billing_city, billing_state, billing_postal_code, billing_country,
            last_conversation, next_conversation, working_as, source, website, sort_order)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("title", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("mobile_phone", ""),
            data.get("company_id"),
            data.get("tags", ""),
            data.get("linkedin_profile", ""),
            data.get("facebook_profile", ""),
            data.get("twitter_profile", ""),
            data.get("calendar_link", ""),
            data.get("source_url", ""),
            data.get("source_page", ""),
            data.get("referring_contact", ""),
            1 if data.get("ideal_client") else 0,
            1 if data.get("ideal_partner") else 0,
            data.get("description", ""),
            data.get("billing_street", ""),
            data.get("billing_city", ""),
            data.get("billing_state", ""),
            data.get("billing_postal_code", ""),
            data.get("billing_country", ""),
            data.get("last_conversation") or None,
            data.get("next_conversation") or None,
            data.get("working_as", ""),
            data.get("source", ""),
            data.get("website", ""),
            data.get("sort_order", 0),
        )
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_contact(new_id)


def update_contact(contact_id, data):
    conn = get_db()
    conn.execute(
        """UPDATE contacts SET
           first_name=?, last_name=?, title=?, email=?, phone=?, mobile_phone=?,
           company_id=?, tags=?, linkedin_profile=?, facebook_profile=?, twitter_profile=?,
           calendar_link=?, source_url=?, source_page=?, referring_contact=?,
           ideal_client=?, ideal_partner=?, description=?,
           billing_street=?, billing_city=?, billing_state=?, billing_postal_code=?, billing_country=?,
           last_conversation=?, next_conversation=?, working_as=?, source=?, website=?,
           updated_at=datetime('now')
           WHERE id=?""",
        (
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("title", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("mobile_phone", ""),
            data.get("company_id"),
            data.get("tags", ""),
            data.get("linkedin_profile", ""),
            data.get("facebook_profile", ""),
            data.get("twitter_profile", ""),
            data.get("calendar_link", ""),
            data.get("source_url", ""),
            data.get("source_page", ""),
            data.get("referring_contact", ""),
            1 if data.get("ideal_client") else 0,
            1 if data.get("ideal_partner") else 0,
            data.get("description", ""),
            data.get("billing_street", ""),
            data.get("billing_city", ""),
            data.get("billing_state", ""),
            data.get("billing_postal_code", ""),
            data.get("billing_country", ""),
            data.get("last_conversation") or None,
            data.get("next_conversation") or None,
            data.get("working_as", ""),
            data.get("source", ""),
            data.get("website", ""),
            contact_id,
        )
    )
    conn.commit()
    conn.close()
    return get_contact(contact_id)


def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM interactions WHERE contact_id=?", (contact_id,))
    conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()


def reorder_contacts(order):
    """order: list of {id, sort_order}"""
    conn = get_db()
    for item in order:
        conn.execute(
            "UPDATE contacts SET sort_order=? WHERE id=?",
            (item["sort_order"], item["id"])
        )
    conn.commit()
    conn.close()


def get_next_call_contact(working_as=None, tags=None):
    """Return contact with nearest next_conversation date, optionally filtered.
    tags: list of tag names — contact must match ANY one (OR logic).
    """
    conn = get_db()
    conditions = ["c.next_conversation IS NOT NULL", "c.next_conversation != ''", "c.is_archived = 0"]
    params = []
    if working_as:
        conditions.append("c.working_as = ?")
        params.append(working_as)
    if tags:
        tag_clauses = ["(',' || c.tags || ',' LIKE ?)" for _ in tags]
        conditions.append("(" + " OR ".join(tag_clauses) + ")")
        params.extend(f"%,{t},%"for t in tags)
    where = "WHERE " + " AND ".join(conditions)
    row = conn.execute(
        f"""SELECT c.*, co.name as company_name
           FROM contacts c
           LEFT JOIN companies co ON c.company_id = co.id
           {where}
           ORDER BY c.next_conversation ASC
           LIMIT 1""",
        params
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def all_contacts_csv(include_archived=False):
    """Return contacts as list of dicts for CSV export."""
    conn = get_db()
    where = "" if include_archived else "WHERE c.is_archived = 0"
    rows = conn.execute(
        f"""SELECT c.*, co.name as company_name
           FROM contacts c
           LEFT JOIN companies co ON c.company_id = co.id
           {where}
           ORDER BY c.sort_order ASC, c.id ASC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def archive_contact(contact_id):
    conn = get_db()
    conn.execute("UPDATE contacts SET is_archived=1, updated_at=datetime('now') WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()
    return get_contact(contact_id)


def unarchive_contact(contact_id):
    conn = get_db()
    conn.execute("UPDATE contacts SET is_archived=0, updated_at=datetime('now') WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()
    return get_contact(contact_id)
