"""
CompaniesDaemon - company CRUD operations.
"""

from daemons.contacts import get_db


def list_companies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM companies ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_or_create_company(name, url=None):
    """Get existing company by name or create it. Returns id."""
    if not name:
        return None
    conn = get_db()
    row = conn.execute("SELECT id FROM companies WHERE name=?", (name,)).fetchone()
    if row:
        conn.close()
        return row["id"]
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (name, url) VALUES (?,?)", (name, url or ""))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id
