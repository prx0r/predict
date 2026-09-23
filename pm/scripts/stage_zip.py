#!/usr/bin/env python3
"""Stage bneck2 zip for email delivery + print send instructions.

Gmail send needs a vault role this session lacks (credential read =
member-only), so this stages /tmp/bneck2-full.zip and outbox/ copy, then
prints the one command that sends it once run with sufficient role.
"""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOX = os.path.join(ROOT, "outbox")
SKIP = {"third_party", "__pycache__", ".git", "outbox"}


def build() -> tuple[str, int, int]:
    os.makedirs(OUTBOX, exist_ok=True)
    dest = "/tmp/bneck2-full.zip"
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for f in files:
                if f.endswith(".pyc"):
                    continue
                p = os.path.join(root, f)
                rel = os.path.relpath(p, ROOT)
                if rel in ("data/prices.jsonl", "data/prices_latest.json"):
                    continue
                z.write(p, rel)
                n += 1
    import shutil
    shutil.copy(dest, os.path.join(OUTBOX, "bneck2-full.zip"))
    size = os.path.getsize(dest)
    return dest, n, size


if __name__ == "__main__":
    dest, n, size = build()
    print(f"staged {dest}: {n} files, {size/1024:.0f} KB")
    print("outbox copy: outbox/bneck2-full.zip")
    print("to send (needs vault member role):")
    print("  AGENT_VAULT_TOKEN=<member-token> python3 scripts/send_gmail.py outbox/bneck2-full.zip tradesprior@gmail.com")
