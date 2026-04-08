from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import logging
import csv
import io

import config
from daemons.auth import (
    login_required, verify_pin, is_locked_out,
    record_failed_attempt, clear_failed_attempts
)
from daemons.contacts import (
    init_schema, list_contacts, get_contact, create_contact,
    update_contact, delete_contact, reorder_contacts,
    get_next_call_contact, all_contacts_csv,
    archive_contact, unarchive_contact
)
from daemons.companies import list_companies, get_or_create_company
from daemons.interactions import list_interactions, log_interaction, delete_interaction
from daemons.settings_daemon import (
    get_all_tags, create_tag, delete_tag, rename_tag,
    get_working_as_options, create_working_as, delete_working_as,
    get_all_sources, create_source, delete_source, rename_source
)
from daemons.importer import import_csv, parse_paste_text, import_enriched_csv
from daemons.campaigns import (
    init_campaigns_schema,
    list_campaigns, create_campaign, update_campaign_notes, delete_campaign,
    archive_campaign, unarchive_campaign,
    add_step, delete_step, reorder_steps,
    get_board, add_contact_to_campaign, remove_contact_from_campaign,
    move_contact_to_step, reorder_contacts_in_step,
    get_contact_campaigns, search_contacts_not_in_campaign
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(config.DATA_DIR / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=24)

# Initialize DB schema on startup
init_schema()
init_campaigns_schema()


def _set_network_cookie(response):
    s = URLSafeTimedSerializer(config.SSO_SECRET)
    value = s.dumps({"net": "hermes"}, salt="network-auth")
    response.set_cookie("network_auth", value, max_age=86400, httponly=True, samesite="Lax")
    return response


@app.before_request
def consume_sso_token():
    if request.endpoint == "login_page":
        return
    if session.get("authenticated"):
        if request.args.get("token"):
            return redirect(request.url.split("?")[0])
        return
    if not config.AUTH_ENABLED:
        return
    s = URLSafeTimedSerializer(config.SSO_SECRET)

    # Check URL token
    token = request.args.get("token")
    if token:
        try:
            data = s.loads(token, salt="sso-cross-app", max_age=300)
            if data.get("sso"):
                session.permanent = True
                session["authenticated"] = True
                resp = redirect(request.url.split("?")[0])
                _set_network_cookie(resp)
                return resp
        except (SignatureExpired, BadSignature):
            pass

    # Check shared network cookie
    net_cookie = request.cookies.get("network_auth")
    if net_cookie:
        try:
            data = s.loads(net_cookie, salt="network-auth", max_age=86400)
            if data.get("net"):
                session.permanent = True
                session["authenticated"] = True
                return
        except (SignatureExpired, BadSignature):
            pass


# ============ Auth Routes ============

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if not config.AUTH_ENABLED:
        session["authenticated"] = True
        return redirect(url_for("leads"))

    if session.get("authenticated"):
        return redirect(url_for("leads"))

    error = None
    locked_seconds = 0

    locked, remaining = is_locked_out()
    if locked:
        return render_template("login.html", error=None, locked_seconds=remaining)

    if request.method == "POST":
        pin = request.form.get("pin", "")
        if verify_pin(pin, config.PIN_HASH):
            clear_failed_attempts()
            session.permanent = True
            session["authenticated"] = True
            resp = redirect(url_for("leads"))
            _set_network_cookie(resp)
            return resp
        else:
            attempts_left, now_locked = record_failed_attempt()
            if now_locked:
                error = "Too many attempts. Locked for 5 minutes."
                locked_seconds = 300
            else:
                error = f"Wrong PIN. {attempts_left} attempts remaining."

    return render_template("login.html", error=error, locked_seconds=locked_seconds)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/api/auth-token")
@login_required
def api_auth_token():
    s = URLSafeTimedSerializer(config.SSO_SECRET)
    token = s.dumps({"sso": "hermes"}, salt="sso-cross-app")
    return jsonify({"token": token})


# ============ Page Routes ============

@app.route("/")
@login_required
def leads():
    return render_template("leads.html")


@app.route("/call")
@login_required
def call_mode():
    return render_template("call.html")


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@app.route("/import")
@login_required
def import_page():
    return render_template("import.html")


@app.route("/campaigns")
@login_required
def campaigns_page():
    return render_template("campaigns.html")


# ============ Contact API ============

@app.route("/api/contacts", methods=["GET"])
@login_required
def api_contacts_list():
    q = request.args.get("q", "").strip()
    tags_raw = request.args.get("tags", "").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None
    working_as = request.args.get("working_as", "").strip()
    source = request.args.get("source", "").strip()
    archived = request.args.get("archived", "active").strip()
    if archived not in ("active", "archived", "all"):
        archived = "active"
    page = int(request.args.get("page", 1))
    sort_by = request.args.get("sort_by", "").strip() or None
    sort_dir = request.args.get("sort_dir", "asc").strip()
    return jsonify(list_contacts(q=q or None, tags=tags, working_as=working_as or None, source=source or None, archived=archived, page=page, sort_by=sort_by, sort_dir=sort_dir))


@app.route("/api/contacts", methods=["POST"])
@login_required
def api_contacts_create():
    data = request.get_json() or {}
    # Resolve company name to id
    company_name = data.pop("company_name", "")
    if company_name and not data.get("company_id"):
        data["company_id"] = get_or_create_company(company_name)
    contact = create_contact(data)
    logger.info(f"Contact created: {contact['first_name']} {contact.get('last_name', '')}")
    return jsonify(contact), 201


@app.route("/api/contacts/<int:contact_id>", methods=["GET"])
@login_required
def api_contact_get(contact_id):
    contact = get_contact(contact_id)
    if not contact:
        return jsonify({"error": "Not found"}), 404
    return jsonify(contact)


@app.route("/api/contacts/<int:contact_id>", methods=["POST"])
@login_required
def api_contact_update(contact_id):
    data = request.get_json() or {}
    company_name = data.pop("company_name", "")
    if company_name and not data.get("company_id"):
        data["company_id"] = get_or_create_company(company_name)
    contact = update_contact(contact_id, data)
    if not contact:
        return jsonify({"error": "Not found"}), 404
    logger.info(f"Contact updated: {contact_id}")
    return jsonify(contact)


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def api_contact_delete(contact_id):
    delete_contact(contact_id)
    logger.info(f"Contact deleted: {contact_id}")
    return jsonify({"ok": True})


@app.route("/api/contacts/<int:contact_id>/archive", methods=["POST"])
@login_required
def api_contact_archive(contact_id):
    data = request.get_json() or {}
    fn = archive_contact if data.get("archived", True) else unarchive_contact
    contact = fn(contact_id)
    if not contact:
        return jsonify({"error": "Not found"}), 404
    action = "archived" if data.get("archived", True) else "unarchived"
    logger.info(f"Contact {action}: {contact_id}")
    return jsonify(contact)


@app.route("/api/contacts/reorder", methods=["POST"])
@login_required
def api_contacts_reorder():
    data = request.get_json() or {}
    order = data.get("order", [])
    reorder_contacts(order)
    return jsonify({"ok": True})


@app.route("/api/contacts/bulk", methods=["POST"])
@login_required
def api_contacts_bulk():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    action = data.get("action", "")
    value = data.get("value", "")
    if not ids:
        return jsonify({"error": "no ids"}), 400
    if action == "add_to_campaign":
        campaign_id = int(value) if value else None
        if not campaign_id:
            return jsonify({"error": "campaign_id required"}), 400
        added = sum(1 for cid in ids if "ok" in add_contact_to_campaign(campaign_id, cid))
        logger.info(f"Bulk add_to_campaign {campaign_id}: {added}/{len(ids)} contacts")
        return jsonify({"ok": True, "count": added})
    from daemons.contacts import get_db
    conn = get_db()
    if action == "delete":
        conn.execute(f"DELETE FROM interactions WHERE contact_id IN ({','.join('?'*len(ids))})", ids)
        conn.execute(f"DELETE FROM contacts WHERE id IN ({','.join('?'*len(ids))})", ids)
    elif action == "set_tag":
        conn.execute(f"UPDATE contacts SET tags=?, updated_at=datetime('now') WHERE id IN ({','.join('?'*len(ids))})", [value] + list(ids))
    elif action == "set_working_as":
        conn.execute(f"UPDATE contacts SET working_as=?, updated_at=datetime('now') WHERE id IN ({','.join('?'*len(ids))})", [value] + list(ids))
    else:
        conn.close()
        return jsonify({"error": "unknown action"}), 400
    conn.commit()
    conn.close()
    logger.info(f"Bulk {action} on {len(ids)} contacts")
    return jsonify({"ok": True, "count": len(ids)})


@app.route("/api/contacts/<int:contact_id>/interactions", methods=["GET"])
@login_required
def api_contact_interactions(contact_id):
    return jsonify(list_interactions(contact_id))


# ============ Interactions API ============

@app.route("/api/interactions", methods=["POST"])
@login_required
def api_interactions_create():
    data = request.get_json() or {}
    contact_id = data.get("contact_id")
    date = data.get("date", "")
    itype = data.get("type", "note")
    notes = data.get("notes", "")
    if not contact_id or not date:
        return jsonify({"error": "contact_id and date required"}), 400
    result = log_interaction(contact_id, date, itype, notes)
    logger.info(f"Interaction logged: contact {contact_id} on {date}")
    return jsonify(result), 201


@app.route("/api/interactions/<int:interaction_id>", methods=["DELETE"])
@login_required
def api_interaction_delete(interaction_id):
    delete_interaction(interaction_id)
    return jsonify({"ok": True})


# ============ Call Mode API ============

@app.route("/api/call/next", methods=["GET"])
@login_required
def api_call_next():
    working_as = request.args.get("working_as", "").strip() or None
    tags_raw = request.args.get("tags", "").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None
    contact = get_next_call_contact(working_as=working_as, tags=tags)
    if not contact:
        return jsonify({"contact": None})
    return jsonify({"contact": contact})


@app.route("/api/call/<int:contact_id>/defer", methods=["POST"])
@login_required
def api_call_defer(contact_id):
    data = request.get_json() or {}
    new_date = data.get("next_conversation", "")
    if not new_date:
        return jsonify({"error": "next_conversation date required"}), 400
    contact = get_contact(contact_id)
    if not contact:
        return jsonify({"error": "Not found"}), 404
    contact["next_conversation"] = new_date
    updated = update_contact(contact_id, contact)
    logger.info(f"Call deferred: contact {contact_id} to {new_date}")
    return jsonify(updated)


# ============ Settings API ============

@app.route("/api/settings", methods=["GET"])
@login_required
def api_settings_get():
    return jsonify({
        "tags": get_all_tags(),
        "working_as_options": get_working_as_options(),
        "sources": get_all_sources(),
    })


@app.route("/api/tags", methods=["POST"])
@login_required
def api_tags_create():
    data = request.get_json() or {}
    result = create_tag(data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/tags/<int:tag_id>", methods=["DELETE"])
@login_required
def api_tags_delete(tag_id):
    delete_tag(tag_id)
    return jsonify({"ok": True})


@app.route("/api/tags/<int:tag_id>", methods=["POST"])
@login_required
def api_tags_rename(tag_id):
    data = request.get_json() or {}
    result = rename_tag(tag_id, data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/working_as", methods=["POST"])
@login_required
def api_working_as_create():
    data = request.get_json() or {}
    result = create_working_as(data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/working_as/<int:option_id>", methods=["DELETE"])
@login_required
def api_working_as_delete(option_id):
    delete_working_as(option_id)
    return jsonify({"ok": True})


@app.route("/api/sources", methods=["POST"])
@login_required
def api_sources_create():
    data = request.get_json() or {}
    result = create_source(data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/sources/<int:source_id>", methods=["DELETE"])
@login_required
def api_sources_delete(source_id):
    delete_source(source_id)
    return jsonify({"ok": True})


@app.route("/api/sources/<int:source_id>", methods=["POST"])
@login_required
def api_sources_rename(source_id):
    data = request.get_json() or {}
    result = rename_source(source_id, data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ============ Campaigns API ============

@app.route("/api/campaigns", methods=["GET"])
@login_required
def api_campaigns_list():
    include_archived = request.args.get("include_archived", "0") == "1"
    return jsonify(list_campaigns(include_archived=include_archived))


@app.route("/api/campaigns", methods=["POST"])
@login_required
def api_campaigns_create():
    data = request.get_json() or {}
    result = create_campaign(data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/campaigns/<int:campaign_id>/notes", methods=["POST"])
@login_required
def api_campaign_notes(campaign_id):
    data = request.get_json() or {}
    return jsonify(update_campaign_notes(campaign_id, data.get("notes", "")))


@app.route("/api/campaigns/<int:campaign_id>", methods=["DELETE"])
@login_required
def api_campaign_delete(campaign_id):
    delete_campaign(campaign_id)
    return jsonify({"ok": True})


@app.route("/api/campaigns/<int:campaign_id>/archive", methods=["POST"])
@login_required
def api_campaign_archive(campaign_id):
    data = request.get_json() or {}
    fn = archive_campaign if data.get("archived", True) else unarchive_campaign
    return jsonify(fn(campaign_id))


@app.route("/api/campaigns/<int:campaign_id>/steps", methods=["POST"])
@login_required
def api_campaign_steps_add(campaign_id):
    data = request.get_json() or {}
    result = add_step(campaign_id, data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/campaigns/<int:campaign_id>/steps/<int:step_id>", methods=["DELETE"])
@login_required
def api_campaign_steps_delete(campaign_id, step_id):
    return jsonify(delete_step(campaign_id, step_id))


@app.route("/api/campaigns/<int:campaign_id>/steps/reorder", methods=["POST"])
@login_required
def api_campaign_steps_reorder(campaign_id):
    data = request.get_json() or {}
    return jsonify(reorder_steps(campaign_id, data.get("order", [])))


@app.route("/api/campaigns/<int:campaign_id>/board", methods=["GET"])
@login_required
def api_campaign_board(campaign_id):
    result = get_board(campaign_id)
    if not result:
        return jsonify({"error": "Not found"}), 404
    return jsonify(result)


@app.route("/api/campaigns/<int:campaign_id>/contacts", methods=["POST"])
@login_required
def api_campaign_contacts_add(campaign_id):
    data = request.get_json() or {}
    result = add_contact_to_campaign(campaign_id, data.get("contact_id"))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/campaigns/<int:campaign_id>/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def api_campaign_contacts_remove(campaign_id, contact_id):
    return jsonify(remove_contact_from_campaign(campaign_id, contact_id))


@app.route("/api/campaigns/<int:campaign_id>/contacts/<int:contact_id>/step", methods=["POST"])
@login_required
def api_campaign_contacts_move(campaign_id, contact_id):
    data = request.get_json() or {}
    result = move_contact_to_step(campaign_id, contact_id, data.get("step_id"))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/campaigns/<int:campaign_id>/contacts/reorder", methods=["POST"])
@login_required
def api_campaign_contacts_reorder(campaign_id):
    data = request.get_json() or {}
    return jsonify(reorder_contacts_in_step(campaign_id, data.get("step_id"), data.get("order", [])))


@app.route("/api/contacts/<int:contact_id>/campaigns", methods=["GET"])
@login_required
def api_contact_campaigns(contact_id):
    return jsonify(get_contact_campaigns(contact_id))


@app.route("/api/campaigns/<int:campaign_id>/search-contacts", methods=["GET"])
@login_required
def api_campaign_search_contacts(campaign_id):
    q = request.args.get("q", "").strip()
    return jsonify(search_contacts_not_in_campaign(campaign_id, q))


# ============ Export / Import ============

@app.route("/api/export/csv", methods=["GET"])
@login_required
def api_export_csv():
    from daemons.contacts import get_db
    include_archived = request.args.get("include_archived", "0") == "1"
    contacts = all_contacts_csv(include_archived=include_archived)

    # Fetch all interactions in one query, group by contact
    conn = get_db()
    irows = conn.execute(
        "SELECT contact_id, date, type, notes FROM interactions ORDER BY contact_id, date DESC"
    ).fetchall()
    conn.close()

    interactions_by_contact = {}
    for r in irows:
        entry = f"{r['date']} | {r['type']}" + (f" | {r['notes']}" if r['notes'] else "")
        interactions_by_contact.setdefault(r['contact_id'], []).append(entry)

    for c in contacts:
        c["interactions"] = "\n".join(interactions_by_contact.get(c["id"], []))

    output = io.StringIO()
    fieldnames = [
        "id", "first_name", "last_name", "title", "email", "phone", "mobile_phone",
        "company_name", "tags", "working_as", "linkedin_profile", "facebook_profile",
        "twitter_profile", "calendar_link", "source_url", "source_page",
        "referring_contact", "ideal_client", "ideal_partner", "description",
        "billing_street", "billing_city", "billing_state", "billing_postal_code",
        "billing_country", "last_conversation", "next_conversation",
        "source", "website",
        "maps_url", "status", "types", "rating", "review_count", "place_id",
        "interactions",
        "created_at", "updated_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(contacts)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=hermes-contacts.csv"}
    )


@app.route("/api/import", methods=["POST"])
@login_required
def api_import():
    import os
    # Default to bundled Mimiran export
    default_csv = str(config.BASE_DIR / "Mimiran Export - mimiran-contact-details-20240615 (1).csv")
    filepath = request.json.get("filepath", default_csv) if request.is_json else default_csv
    if not os.path.exists(filepath):
        return jsonify({"error": f"File not found: {filepath}"}), 400
    result = import_csv(filepath)
    logger.info(f"Import complete: {result}")
    return jsonify(result)


@app.route("/api/import/enriched", methods=["POST"])
@login_required
def api_import_enriched():
    import os, tempfile
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        f.save(tmp.name)
        tmppath = tmp.name
    try:
        result = import_enriched_csv(tmppath)
    finally:
        os.unlink(tmppath)
    logger.info(f"Enriched import complete: {result}")
    return jsonify(result)


@app.route("/api/contacts/paste-import", methods=["POST"])
@login_required
def paste_import():
    text = (request.json or {}).get("text", "")
    if not text.strip():
        return jsonify({"error": "No text provided"}), 400
    data = parse_paste_text(text)
    company_name = data.pop("company_name", "")
    if company_name:
        data["company_id"] = get_or_create_company(company_name)
    contact = create_contact(data)
    return jsonify(contact)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=config.PORT)
