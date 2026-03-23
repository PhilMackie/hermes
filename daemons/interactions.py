"""
InteractionsDaemon - interaction log operations.
"""

from daemons.contacts import get_db


def list_interactions(contact_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM interactions WHERE contact_id=? ORDER BY date DESC, id DESC",
        (contact_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_interaction(contact_id, date, itype, notes=""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO interactions (contact_id, date, type, notes) VALUES (?,?,?,?)",
        (contact_id, date, itype, notes)
    )
    # Update last_conversation on contact if this date is newer
    conn.execute(
        """UPDATE contacts
           SET last_conversation = ?,
               updated_at = datetime('now')
           WHERE id = ? AND (last_conversation IS NULL OR last_conversation < ?)""",
        (date, contact_id, date)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "contact_id": contact_id, "date": date, "type": itype, "notes": notes}


def delete_interaction(interaction_id):
    conn = get_db()
    conn.execute("DELETE FROM interactions WHERE id=?", (interaction_id,))
    conn.commit()
    conn.close()
