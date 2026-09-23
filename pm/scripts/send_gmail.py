#!/usr/bin/env python3
"""Send a file via Gmail API using vaulted OAuth creds (stdlib only).

Usage: python3 scripts/send_gmail.py <file> <to> [--subject S]
Requires AGENT_VAULT_* env (member role) — fetches GMAIL_CLIENT_ID,
GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN from the oracle vault, mints an
access token, sends via gmail.users.messages.send. Prints only status.
"""
from __future__ import annotations

import base64
import email.message
import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import urllib.request

VAULT = os.environ.get("AGENT_VAULT_VAULT", "oracle")


def vault_get(key: str) -> str:
    env = dict(os.environ)
    r = subprocess.run(["agent-vault", "vault", "credential", "get", key,
                        "--vault", VAULT], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"vault read failed for {key}: {r.stderr.strip()[:100]}")
    return r.stdout.strip().splitlines()[-1]


def access_token(cid: str, secret: str, refresh: str) -> str:
    body = urllib.parse.urlencode(
        {"client_id": cid, "client_secret": secret,
         "refresh_token": refresh, "grant_type": "refresh_token"}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def send(to: str, path: str, subject: str) -> str:
    cid = vault_get("GMAIL_CLIENT_ID")
    secret = vault_get("GMAIL_CLIENT_SECRET")
    refresh = vault_get("GMAIL_REFRESH_TOKEN")
    token = access_token(cid, secret, refresh)
    msg = email.message.EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("bneck2 full project zip attached (engine + data + docs + messages, clones excluded with URL manifest).")
    ctype, _ = mimetypes.guess_type(path)
    maintype, subtype = (ctype or "application/zip").split("/", 1)
    msg.add_attachment(open(path, "rb").read(), maintype=maintype, subtype=subtype,
                       filename=os.path.basename(path))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()).get("id", "")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: send_gmail.py <file> <to> [--subject S]", file=sys.stderr)
        raise SystemExit(2)
    path, to = sys.argv[1], sys.argv[2]
    subj = "bneck2 project zip"
    if "--subject" in sys.argv:
        subj = sys.argv[sys.argv.index("--subject") + 1]
    mid = send(to, path, subj)
    print(f"sent id={mid}")
