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

# Build lookup by BOTH doi and title so a paper that got its DOI backfilled
# after the original blank-DOI entry was created is still matched correctly.
doi_to_idx: dict[str, int] = {}
title_to_idx: dict[str, int] = {}
for i, p in enumerate(origin):
    doi = (p.get("doi") or "").strip().lower()
    title = (p.get("title") or "").strip().lower()
    if doi:
        doi_to_idx[doi] = i
    if title:
        title_to_idx[title] = i


def _find_origin_idx(p: dict) -> int | None:
    """Return origin index matching by DOI first, then title."""
    doi = (p.get("doi") or "").strip().lower()
    title = (p.get("title") or "").strip().lower()
    if doi and doi in doi_to_idx:
        return doi_to_idx[doi]
    if title and title in title_to_idx:
        return title_to_idx[title]
    return None


MERGE_FIELDS = ("authors", "author_data", "curated", "pdf_link", "summary", "relevance", "tags", "score")

merged = list(origin)
added = 0
updated = 0
for p in local:
    idx = _find_origin_idx(p)
    if idx is None:
        new_idx = len(merged)
        merged.append(p)
        doi = (p.get("doi") or "").strip().lower()
        title = (p.get("title") or "").strip().lower()
        if doi:
            doi_to_idx[doi] = new_idx
        if title:
            title_to_idx[title] = new_idx
        added += 1
    else:
        changed = False
        for field in MERGE_FIELDS:
            if p.get(field) and not merged[idx].get(field):
                merged[idx][field] = p[field]
                changed = True
        if changed:
            updated += 1

with open("papers.json", "w") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Merged: +{added} new paper(s), {updated} updated, {len(merged)} total")
if added == 0 and updated == 0:
    sys.exit(42)
