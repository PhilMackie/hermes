"""
CampaignsDaemon - campaign kanban board CRUD.
"""

from daemons.contacts import get_db


def init_campaigns_schema():
    conn = get_db()
    conn.cursor().executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS campaign_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS contact_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            campaign_id INTEGER NOT NULL,
            step_id INTEGER NOT NULL,
            position INTEGER DEFAULT 0,
            added_at TEXT DEFAULT (datetime('now')),
            UNIQUE(contact_id, campaign_id)
        );
    """)
    conn.commit()

    # Migration: add is_archived if missing
    try:
        conn.execute("ALTER TABLE campaigns ADD COLUMN is_archived INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    conn.close()


def list_campaigns(include_archived=False):
    conn = get_db()
    where = "" if include_archived else "WHERE c.is_archived = 0"
    rows = conn.execute(
        f"""SELECT c.id, c.name, c.notes, c.is_archived,
                  (SELECT COUNT(*) FROM campaign_steps cs WHERE cs.campaign_id = c.id) AS step_count
           FROM campaigns c {where} ORDER BY c.name ASC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def archive_campaign(campaign_id):
    conn = get_db()
    conn.execute("UPDATE campaigns SET is_archived=1 WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def unarchive_campaign(campaign_id):
    conn = get_db()
    conn.execute("UPDATE campaigns SET is_archived=0 WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def create_campaign(name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO campaigns (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"id": new_id, "name": name, "notes": ""}
    except Exception:
        conn.close()
        return {"error": "Campaign name already exists"}


def update_campaign_notes(campaign_id, notes):
    conn = get_db()
    conn.execute("UPDATE campaigns SET notes=? WHERE id=?", (notes, campaign_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def delete_campaign(campaign_id):
    conn = get_db()
    conn.execute("DELETE FROM contact_campaigns WHERE campaign_id=?", (campaign_id,))
    conn.execute("DELETE FROM campaign_steps WHERE campaign_id=?", (campaign_id,))
    conn.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()


def add_step(campaign_id, name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM campaign_steps WHERE campaign_id=?",
            (campaign_id,)
        ).fetchone()
        pos = row["pos"]
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO campaign_steps (campaign_id, name, position) VALUES (?, ?, ?)",
            (campaign_id, name, pos)
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"id": new_id, "name": name, "position": pos}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


def delete_step(campaign_id, step_id):
    conn = get_db()
    # Find prev step by position
    step = conn.execute(
        "SELECT position FROM campaign_steps WHERE id=? AND campaign_id=?",
        (step_id, campaign_id)
    ).fetchone()
    if step:
        prev = conn.execute(
            "SELECT id FROM campaign_steps WHERE campaign_id=? AND position < ? ORDER BY position DESC LIMIT 1",
            (campaign_id, step["position"])
        ).fetchone()
        if prev:
            conn.execute(
                "UPDATE contact_campaigns SET step_id=? WHERE campaign_id=? AND step_id=?",
                (prev["id"], campaign_id, step_id)
            )
        else:
            conn.execute(
                "DELETE FROM contact_campaigns WHERE campaign_id=? AND step_id=?",
                (campaign_id, step_id)
            )
    conn.execute("DELETE FROM campaign_steps WHERE id=? AND campaign_id=?", (step_id, campaign_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def reorder_steps(campaign_id, ordered_ids):
    conn = get_db()
    for i, sid in enumerate(ordered_ids):
        conn.execute(
            "UPDATE campaign_steps SET position=? WHERE id=? AND campaign_id=?",
            (i, sid, campaign_id)
        )
    conn.commit()
    conn.close()
    return {"ok": True}


def get_board(campaign_id):
    conn = get_db()
    campaign = conn.execute(
        "SELECT id, name, notes FROM campaigns WHERE id=?", (campaign_id,)
    ).fetchone()
    if not campaign:
        conn.close()
        return None
    steps = conn.execute(
        "SELECT id, name, position FROM campaign_steps WHERE campaign_id=? ORDER BY position ASC",
        (campaign_id,)
    ).fetchall()
    cards = conn.execute(
        """SELECT cc.contact_id, cc.step_id, cc.position,
                  c.first_name, c.last_name, c.tags, co.name as company_name
           FROM contact_campaigns cc
           JOIN contacts c ON cc.contact_id = c.id
           LEFT JOIN companies co ON c.company_id = co.id
           WHERE cc.campaign_id = ?
           ORDER BY cc.step_id, cc.position ASC""",
        (campaign_id,)
    ).fetchall()
    conn.close()
    cards_by_step = {}
    for card in cards:
        sid = card["step_id"]
        if sid not in cards_by_step:
            cards_by_step[sid] = []
        cards_by_step[sid].append(dict(card))
    return {
        "campaign": dict(campaign),
        "steps": [dict(s) for s in steps],
        "cards_by_step": cards_by_step,
    }


def add_contact_to_campaign(campaign_id, contact_id):
    conn = get_db()
    first_step = conn.execute(
        "SELECT id FROM campaign_steps WHERE campaign_id=? ORDER BY position ASC LIMIT 1",
        (campaign_id,)
    ).fetchone()
    if not first_step:
        conn.close()
        return {"error": "Campaign has no steps"}
    step_id = first_step["id"]
    try:
        conn.execute(
            "INSERT INTO contact_campaigns (contact_id, campaign_id, step_id, position) VALUES (?, ?, ?, 0)",
            (contact_id, campaign_id, step_id)
        )
        conn.commit()
        conn.close()
        return {"ok": True, "step_id": step_id}
    except Exception:
        conn.close()
        return {"error": "Contact already in campaign"}


def remove_contact_from_campaign(campaign_id, contact_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM contact_campaigns WHERE campaign_id=? AND contact_id=?",
        (campaign_id, contact_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}


def move_contact_to_step(campaign_id, contact_id, step_id):
    conn = get_db()
    # Verify step belongs to campaign
    step = conn.execute(
        "SELECT id FROM campaign_steps WHERE id=? AND campaign_id=?",
        (step_id, campaign_id)
    ).fetchone()
    if not step:
        conn.close()
        return {"error": "Step not found"}
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM contact_campaigns WHERE campaign_id=? AND step_id=?",
        (campaign_id, step_id)
    ).fetchone()
    pos = row["pos"]
    conn.execute(
        "UPDATE contact_campaigns SET step_id=?, position=? WHERE campaign_id=? AND contact_id=?",
        (step_id, pos, campaign_id, contact_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}


def reorder_contacts_in_step(campaign_id, step_id, ordered_contact_ids):
    conn = get_db()
    for i, cid in enumerate(ordered_contact_ids):
        conn.execute(
            "UPDATE contact_campaigns SET position=? WHERE campaign_id=? AND step_id=? AND contact_id=?",
            (i, campaign_id, step_id, cid)
        )
    conn.commit()
    conn.close()
    return {"ok": True}


def get_contact_campaigns(contact_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT cc.campaign_id, cam.name as campaign_name, cc.step_id, cs.name as step_name
           FROM contact_campaigns cc
           JOIN campaigns cam ON cc.campaign_id = cam.id
           JOIN campaign_steps cs ON cc.step_id = cs.id
           WHERE cc.contact_id = ?
           ORDER BY cam.name ASC""",
        (contact_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_contacts_not_in_campaign(campaign_id, q):
    conn = get_db()
    q_like = f"%{q}%"
    rows = conn.execute(
        """SELECT c.id, c.first_name, c.last_name, co.name as company_name
           FROM contacts c
           LEFT JOIN companies co ON c.company_id = co.id
           WHERE c.is_archived = 0
             AND (c.first_name LIKE ? OR c.last_name LIKE ? OR co.name LIKE ?)
             AND c.id NOT IN (
                 SELECT contact_id FROM contact_campaigns WHERE campaign_id=?
             )
           ORDER BY c.first_name, c.last_name
           LIMIT 15""",
        (q_like, q_like, q_like, campaign_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
