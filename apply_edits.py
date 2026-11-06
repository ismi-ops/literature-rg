"""Apply edits sent from the site's gear menu to papers.json, then regenerate the site.

The EDITS environment variable holds a JSON list; each item identifies a paper by `key`
(its DOI, or its title when it has none) and carries any of:
    {"key": "10.1038/...", "ru_pick": true}        mark / unmark as one of Ru's picks
    {"key": "10.1038/...", "pdf_link": "https://…"} set the PDF link ("" clears it)
    {"key": "10.1038/...", "delete": true}          remove from the list (soft delete: sets `rejected`,
                                                    so the agent will not add the paper again)
"""
import json
import os
import sys

import generate_site
from src import storage

MAX_EDITS = 200


def _key(paper: dict) -> str:
    return ((paper.get("doi") or "").strip() or (paper.get("title") or "").strip()).lower()


def _valid_pdf_link(value) -> bool:
    return isinstance(value, str) and (
        value == "" or value.startswith("https://") or (value.startswith("pdfs/") and value.endswith(".pdf"))
    )


def apply_edits(papers: list[dict], edits: list[dict]) -> int:
    """Apply edits in place; returns how many papers changed."""
    by_key = {}
    for p in papers:
        by_key.setdefault(_key(p), p)
    changed = 0
    for edit in edits[:MAX_EDITS]:
        key = str(edit.get("key") or "").strip().lower()
        paper = by_key.get(key) if key else None
        if paper is None:
            print(f"  skip: no paper matches key {key[:60]!r}")
            continue
        before = json.dumps(paper, sort_keys=True)
        if edit.get("delete") is True:
            paper["rejected"] = True
        if isinstance(edit.get("ru_pick"), bool):
            if edit["ru_pick"]:
                paper["ru_pick"] = True
            else:
                paper.pop("ru_pick", None)
        if "pdf_link" in edit:
            if _valid_pdf_link(edit["pdf_link"]):
                paper["pdf_link"] = edit["pdf_link"]
            else:
                print(f"  skip pdf_link for {key[:60]!r}: must be https://… or pdfs/….pdf")
        if json.dumps(paper, sort_keys=True) != before:
            changed += 1
            print(f"  edited: {(paper.get('title') or '')[:70]}")
    return changed


def main():
    try:
        edits = json.loads(os.environ.get("EDITS", "[]"))
    except json.JSONDecodeError as e:
        sys.exit(f"EDITS is not valid JSON: {e}")
    if not isinstance(edits, list):
        sys.exit("EDITS must be a JSON list")
    papers = storage.load_papers()
    changed = apply_edits(papers, [e for e in edits if isinstance(e, dict)])
    if changed:
        storage.save_papers(papers)
    print(f"{changed} edit(s) changed something.")
    generate_site.main()


if __name__ == "__main__":
    main()
