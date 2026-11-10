"""Audit every tile's title/link against Crossref and tidy title formatting.

For each live tile with a DOI the Crossref title is fetched and compared (letters/digits only):
  same       title matches
  partial    one title contains the other (subtitle / truncation)  -> reported
  different  the tile's title is not the paper's title            -> reported; with --fix it is
             replaced when the tile is a converted preprint (previous_dois set) or the tile title is ALL CAPS
  missing    DOI not found in Crossref                            -> reported
Also reported: DOI tiles whose link is a doi.org URL for a different DOI (fixed with --fix),
bioRxiv-DOI tiles that link to a journal site (stale DOI), and tiles with no DOI/title/link.
--fix always applies the shared formatting rules (src/title_clean.py): markup, extra spaces, trailing full stop.

Usage:
    python audit_titles.py            # report only
    python audit_titles.py --fix      # apply the safe fixes to papers.json
"""
import argparse
import os
import re
import time

from src import storage
from src.sources import preprint_status as ps
from src.title_clean import clean_title, norm


def classify(tile_title: str, ref_title: str) -> str:
    a, b = norm(tile_title), norm(ref_title)
    if not b:
        return "missing"
    if a == b:
        return "same"
    if a and (a in b or b in a):
        return "partial"
    return "different"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only audit the first N tiles (testing)")
    args = ap.parse_args()

    papers = storage.load_papers()
    live = [p for p in papers if not p.get("rejected")]
    if args.limit:
        live = live[: args.limit]
    report, fixed = [], 0

    def note(kind, p, detail):
        report.append((kind, (p.get("title") or "")[:90], p.get("doi") or "", detail))

    for i, p in enumerate(live, 1):
        title = p.get("title") or ""
        tidy = clean_title(title)
        if tidy != title:
            note("format", p, f"-> {tidy[:90]}")
            if args.fix:
                p["title"] = title = tidy
                fixed += 1
        doi = (p.get("doi") or "").strip()
        link = (p.get("link") or "").strip()
        if not tidy:
            note("no-title", p, link)
        if not doi:
            if not link:
                note("no-link", p, "no DOI and no link")
            continue
        if not link:
            note("no-link", p, "DOI but no link")
        m = re.match(r"https?://(?:dx\.)?doi\.org/(.+)$", link, re.I)
        if m and m.group(1).strip().lower() != doi.lower():
            note("link-doi", p, f"link {link} != doi")
            if args.fix:
                p["link"] = f"https://doi.org/{doi}"
                fixed += 1
        if doi.lower().startswith(ps.BIORXIV_PREFIXES) and link and not re.search(r"biorxiv|medrxiv|doi\.org", link, re.I):
            note("stale-doi", p, f"bioRxiv DOI but links to {link[:70]} (published? run Check Preprints --force)")
        if doi.lower().startswith("10.48550/"):
            continue   # arXiv: DataCite, not Crossref
        ref = ps.crossref_details(doi)
        kind = classify(title, ref["title"])
        if kind == "missing":
            note("not-in-crossref", p, "")
        elif kind != "same":
            auto = kind == "different" and (p.get("previous_dois") or (title.isupper() and not ref["title"].isupper()))
            auto = auto or (kind == "partial" and title.isupper() and not ref["title"].isupper())
            note(kind, p, f"crossref: {ref['title'][:90]}" + ("  [fixed]" if (auto and args.fix) else ""))
            if auto and args.fix:
                p["title"] = ref["title"]
                fixed += 1
        time.sleep(0.15)
        if i % 50 == 0:
            print(f"  ...{i}/{len(live)}")

    order = ["different", "partial", "stale-doi", "link-doi", "not-in-crossref", "no-title", "no-link", "format"]
    lines = []
    for kind in order:
        rows = [r for r in report if r[0] == kind]
        if rows:
            lines.append(f"\n## {kind} ({len(rows)})")
            lines += [f"- {t} | {d} | {x}" for _, t, d, x in rows]
    print("\n".join(lines) or "Nothing to report.")
    print(f"\n{len(live)} tiles audited, {len(report)} findings, {fixed} fixed.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Title audit\n\n{len(live)} tiles, {len(report)} findings, {fixed} fixed.\n" + "\n".join(lines) + "\n")
    if args.fix and fixed:
        storage.save_papers(papers)


if __name__ == "__main__":
    main()
