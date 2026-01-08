from flask import Flask, request
import requests
import os

app = Flask(__name__)

SUPERCHAT_KEY = os.environ.get("SUPERCHAT_KEY")
ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_USER = os.environ.get("ODOO_USER")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD")

def odoo_login():
    url = f"{ODOO_URL}/jsonrpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "login",
            "args": [ODOO_DB, ODOO_USER, ODOO_PASSWORD]
        },
        "id": 1
    }
    r = requests.post(url, json=payload).json()
    return r["result"]

@app.route("/superchat/incoming", methods=["POST"])
def incoming():
    data = request.json

    message = data.get("text", "")
    sender = data.get("from", "")
    file_url = data.get("file_url")

    body = f"From: {sender}\n\n{message}"
    if file_url:
        body += f"\n\nFile: {file_url}"

    uid = odoo_login()

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "mail.channel",
                "message_post",
                [[1]],
                {"body": body}
            ]
        },
        "id": 2
    }

    requests.post(f"{ODOO_URL}/jsonrpc", json=payload)
    return {"status": "ok"}
