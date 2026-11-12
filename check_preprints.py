"""Audit the preprints in papers.json and update any tile whose paper has since been published.

For each preprint not checked in the last RECHECK_DAYS days, look up its published version
(bioRxiv/medRxiv, arXiv, Crossref). When found, the tile is updated in place:
  doi / link / title / journal / year -> the published article
  preprint flag                -> removed
  previous_dois                -> keeps the preprint DOI (notes and history follow the tile)
  published_on                 -> today (the site shows a "Published" badge for a month)
If the published article is already in the list as its own tile, the preprint tile is retired
instead (rejected, superseded_by set) and keeps nothing a second copy would show twice;
a Ru's-pick or collaborator mark moves to the surviving tile.

Usage:
    python check_preprints.py                 # check everything that is due
    python check_preprints.py --dry-run       # report only
    python check_preprints.py --force         # ignore the recheck interval
"""
import argparse
import os
import time
from datetime import date, timedelta

from src import storage
from src.sources import preprint_status as ps
from src.sources.pdf_finder import get_pdf_link

RECHECK_DAYS = 21
DEFAULT_LIMIT = 150
PREPRINT_HOSTS = ("biorxiv", "medrxiv", "arxiv")


def is_due(p: dict, today: date, force: bool = False) -> bool:
    if not p.get("preprint") or p.get("rejected") or not (p.get("doi") or "").strip():
        return False
    if force or not p.get("preprint_checked"):
        return True
    try:
        return today - date.fromisoformat(p["preprint_checked"]) >= timedelta(days=RECHECK_DAYS)
    except ValueError:
        return True


def apply_publication(papers: list[dict], p: dict, info: dict, today: date) -> str:
    """Update p (or retire it) given the published article `info`. Returns 'updated' or 'merged'."""
    new_doi = ps._clean(info["doi"])
    old_doi = (p.get("doi") or "").strip()
    twin = next((q for q in papers if q is not p and not q.get("rejected") and ps._clean(q.get("doi") or "") == new_doi), None)
    if twin is not None:
        p["rejected"] = True
        p["superseded_by"] = new_doi
        p["preprint_checked"] = today.isoformat()
        for field in ("ru_pick", "vip_author"):
            if p.get(field) and not twin.get(field):
                twin[field] = p[field]
        twin["previous_dois"] = sorted(set((twin.get("previous_dois") or []) + [old_doi]))
        return "merged"

    details = ps.crossref_details(new_doi)   # the published title often differs from the preprint's
    journal = info.get("journal") or details["journal"]
    year = info.get("year") or details["year"]
    p["previous_dois"] = sorted(set((p.get("previous_dois") or []) + [old_doi]))
    p["doi"] = new_doi
    if details["title"]:
        p["title"] = details["title"]
    p["link"] = f"https://doi.org/{new_doi}"
    if journal:
        p["journal"] = journal
    if year:
        p["year"] = year
    p.pop("preprint", None)
    p["published_on"] = today.isoformat()
    p["preprint_checked"] = today.isoformat()
    cur = p.get("pdf_link") or ""
    if cur.startswith("http") and any(h in cur for h in PREPRINT_HOSTS):   # a preprint-server PDF: prefer the published OA copy
        try:
            better = get_pdf_link({"doi": new_doi, "link": p["link"]})
        except Exception:
            better = None
        if better:
            p["pdf_link"] = better
    return "updated"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="max preprints to check in one run")
    args = ap.parse_args()

    today = date.today()
    papers = storage.load_papers()
    due = [p for p in papers if is_due(p, today, args.force)][: args.limit]
    total = sum(1 for p in papers if p.get("preprint") and not p.get("rejected"))
    print(f"{total} preprints in the list, {len(due)} due for a check.")

    lines, unknown = [], 0
    for i, p in enumerate(due, 1):
        title = (p.get("title") or "")[:70]
        info, reliable = ps.lookup_published(p["doi"])
        if info:
            if args.dry_run:
                outcome = "would update"
            else:
                outcome = apply_publication(papers, p, info, today)
            line = f"{outcome}: {title} -> {info['doi']}" + (f" ({info['journal']})" if info.get("journal") else "")
            print(f"  [{i}/{len(due)}] {line}")
            lines.append(line)
        else:
            if reliable and not args.dry_run:
                p["preprint_checked"] = today.isoformat()
            if not reliable:
                unknown += 1
        time.sleep(0.4)

    print(f"\n{len(lines)} preprint(s) now published; {unknown} could not be checked (service errors, will retry).")
    if not args.dry_run and due:
        storage.save_papers(papers)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Preprint audit\n\n{total} preprints, {len(due)} checked, **{len(lines)} newly published**, {unknown} unreachable.\n\n")
            f.write("".join(f"- {l}\n" for l in lines))


if __name__ == "__main__":
    main()
