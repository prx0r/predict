"""House clerk collector — filing index metadata, keyless ($0).

disclosures-clerk.house.gov Year-to-Date ZIPs list every financial
disclosure filing (member, doc id, date). Per-filing PTR PDFs need PDF
text extraction (no pdf lib on box) — index counts flow now, tickers join
when parsing lands (capitol-api recipe cloned in third_party/).
Senate side needs a browser session (Quantgress scrape_senate.py recipe).
"""
from __future__ import annotations

import io
import urllib.request
import zipfile

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "Chrome/126.0 Safari/537.36")}
BASE = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs"


def yearly_index(year: int = 2026, timeout: int = 60) -> list[dict]:
    """[{member, doc_id, date}] from the YTD index ZIP (names only)."""
    try:
        req = urllib.request.Request(f"{BASE}/{year}FD.zip", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            blob = r.read()
        out = []
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = next((n for n in z.namelist() if n.endswith(".txt")),
                        z.namelist()[0])
            lines = z.read(name).decode("utf-8", "replace").splitlines()
            if not lines:
                return []
            cols = [c.strip() for c in lines[0].split("\t")]
            idx = {c: i for i, c in enumerate(cols)}
            for line in lines[1:]:
                parts = line.split("\t")
                try:
                    out.append({
                        "member": f"{parts[idx.get('First', 2)].strip()} "
                                  f"{parts[idx.get('Last', 1)].strip()}".strip()[:60],
                        "filing_type": parts[idx.get("FilingType", 4)].strip() if len(parts) > 4 else "",
                        "doc_id": parts[idx.get("DocID", 8)].strip() if len(parts) > 8 else "",
                        "date": parts[idx.get("FilingDate", 7)].strip() if len(parts) > 7 else ""})
                except IndexError:
                    continue
        return out
    except Exception:
        return []
