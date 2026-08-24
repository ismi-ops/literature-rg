"""
Merge /tmp/processed_papers.json (our run's output) into origin/main:papers.json.
Called inside the add_paper workflow's retry push loop.
Exits 42 when the paper already exists in origin — caller treats this as "nothing to do".
"""
import json
import subprocess
import sys

with open("/tmp/processed_papers.json") as f:
    local = json.load(f)

try:
    raw = subprocess.check_output(["git", "show", "origin/main:papers.json"]).decode()
    origin = json.loads(raw)
except Exception:
    origin = []

by_key = {}
for i, p in enumerate(origin):
    k = (p.get("doi") or "").strip().lower() or (p.get("title") or "").strip().lower()
    if k:
        by_key[k] = i

merged = list(origin)
added = 0
for p in local:
    k = (p.get("doi") or "").strip().lower() or (p.get("title") or "").strip().lower()
    if not k:
        continue
    if k not in by_key:
        by_key[k] = len(merged)
        merged.append(p)
        added += 1
    else:
        idx = by_key[k]
        for field in ("authors", "pdf_link"):
            if p.get(field) and not merged[idx].get(field):
                merged[idx][field] = p[field]

with open("papers.json", "w") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Merged: +{added} new paper(s), {len(merged)} total")
if added == 0:
    sys.exit(42)
