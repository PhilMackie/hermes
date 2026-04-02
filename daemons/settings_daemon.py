"""
Settings - tags and working_as_options management.
"""

from daemons.contacts import get_db


def get_all_tags():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tags ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_tag(name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"id": new_id, "name": name}
    except Exception:
        conn.close()
        return {"error": "Tag already exists"}


def delete_tag(tag_id):
    conn = get_db()
    conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    conn.commit()
    conn.close()


def rename_tag(tag_id, name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        conn.execute("UPDATE tags SET name=? WHERE id=?", (name, tag_id))
        conn.commit()
        conn.close()
        return {"id": tag_id, "name": name}
    except Exception:
        conn.close()
        return {"error": "Tag name already exists"}


def get_working_as_options():
    conn = get_db()
    rows = conn.execute("SELECT * FROM working_as_options ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_working_as(name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO working_as_options (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"id": new_id, "name": name}
    except Exception:
        conn.close()
        return {"error": "Already exists"}


def delete_working_as(option_id):
    conn = get_db()
    conn.execute("DELETE FROM working_as_options WHERE id=?", (option_id,))
    conn.commit()
    conn.close()


def get_all_sources():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sources ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_source(name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO sources (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return {"id": new_id, "name": name}
    except Exception:
        conn.close()
        return {"error": "Source already exists"}


def delete_source(source_id):
    conn = get_db()
    conn.execute("DELETE FROM sources WHERE id=?", (source_id,))
    conn.commit()
    conn.close()


def rename_source(source_id, name):
    name = name.strip()
    if not name:
        return {"error": "name required"}
    conn = get_db()
    try:
        conn.execute("UPDATE sources SET name=? WHERE id=?", (name, source_id))
        conn.commit()
        conn.close()
        return {"id": source_id, "name": name}
    except Exception:
        conn.close()
        return {"error": "Source name already exists"}
