from flask import Flask, request
import requests
import os

app = Flask(__name__)

SUPERCHAT_KEY = os.environ.get("SUPERCHAT_KEY", "").strip()
ODOO_URL = os.environ.get("ODOO_URL", "").strip().rstrip("/")
ODOO_DB = os.environ.get("ODOO_DB", "").strip()
ODOO_USER = os.environ.get("ODOO_USER", "").strip()
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "").strip()

def odoo_jsonrpc(params, session=None):
    url = f"{ODOO_URL}/jsonrpc"
    payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
    s = session or requests.Session()
    r = s.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise Exception(data["error"])
    return data["result"], s

def odoo_auth():
    result, s = odoo_jsonrpc({
        "service": "common",
        "method": "authenticate",
        "args": [ODOO_DB, ODOO_USER, ODOO_PASSWORD, {}]
    })
    if not result:
        raise Exception("Odoo auth failed (check ODOO_DB/USER/PASSWORD)")
    return result, s

def get_or_create_channel(uid, s, name="Superchat Inbox"):
    # search channel by name
    channel_ids, _ = odoo_jsonrpc({
        "service": "object",
        "method": "execute_kw",
        "args": [ODOO_DB, uid, ODOO_PASSWORD, "mail.channel", "search", [[["name", "=", name]]]],
    }, session=s)

    if channel_ids:
        return channel_ids[0]

    # create channel
    channel_id, _ = odoo_jsonrpc({
        "service": "object",
        "method": "execute_kw",
        "args": [ODOO_DB, uid, ODOO_PASSWORD, "mail.channel", "create", [{
            "name": name,
            "channel_type": "channel",
        }]],
    }, session=s)
    return channel_id

def post_message(uid, s, channel_id, body):
    _, _ = odoo_jsonrpc({
        "service": "object",
        "method": "execute_kw",
        "args": [ODOO_DB, uid, ODOO_PASSWORD, "mail.channel", "message_post", [[channel_id]], {
            "body": body.replace("\n", "<br/>"),
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        }],
    }, session=s)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/superchat/incoming")
def incoming():
    # Optional simple auth (only if you later send a header from Superchat)
    # token = request.headers.get("Authorization", "").strip()
    # if token != SUPERCHAT_KEY:
    #     return {"error": "unauthorized"}, 401

    data = request.get_json(silent=True) or {}

    text = data.get("text") or data.get("message") or ""
    sender = data.get("from") or data.get("sender") or ""
    file_url = data.get("file_url") or data.get("attachment_url") or ""

    body = f"<b>From:</b> {sender}<br/><br/>{text}"
    if file_url:
        body += f"<br/><br/><b>File:</b> <a href='{file_url}'>open</a>"

    uid, s = odoo_auth()
    channel_id = get_or_create_channel(uid, s, "Superchat Inbox")
    post_message(uid, s, channel_id, body)

    return {"status": "ok"}
