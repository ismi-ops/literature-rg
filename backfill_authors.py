"""
Backfill missing or incomplete author lists from Semantic Scholar.

Searches by DOI first (exact), then falls back to title search with
a similarity check to avoid false matches. Updates authors and fills
in any missing DOIs in the process.
"""
import time
import requests
from difflib import SequenceMatcher
from src import storage
from src.sources.semantic_scholar import FIELDS

SS_BASE = "https://api.semanticscholar.org/graph/v1"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "literature-rg/1.0 (mailto:isabelle.smith@alleninstitute.org)"

AUTHOR_FIELDS = "paperId,title,authors,externalIds,publicationDate,year"


def _fmt_authors(ss_authors: list) -> str:
    names = [a.get("name", "") for a in ss_authors if a.get("name")]
    if not names:
        return ""
    # SS returns full names; trim to first 8 then et al.
    if len(names) > 8:
        return ", ".join(names[:8]) + " et al."
    return ", ".join(names)


def _is_incomplete(authors: str) -> bool:
    """True if authors field is blank or looks like last-name-only entries."""
    if not authors or not authors.strip():
        return True
    parts = [p.strip() for p in authors.split(",") if p.strip()]
    # If every part is a single word, it's last-name only
    return all(len(p.split()) == 1 for p in parts)


def _lookup_by_doi(doi: str) -> dict | None:
    try:
        r = _SESSION.get(
            f"{SS_BASE}/paper/DOI:{doi}",
            params={"fields": AUTHOR_FIELDS},
            timeout=15,
        )
        time.sleep(0.5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    DOI lookup error: {e}")
    return None


def _lookup_by_title(title: str) -> dict | None:
    """Search SS by title; return best match if similarity ≥ 0.85."""
    try:
        r = _SESSION.get(
            f"{SS_BASE}/paper/search",
            params={"query": title, "fields": AUTHOR_FIELDS, "limit": 3},
            timeout=15,
        )
        time.sleep(0.5)
        if r.status_code != 200:
            return None
        results = r.json().get("data", [])
        for candidate in results:
            ct = candidate.get("title") or ""
            score = SequenceMatcher(None, title.lower(), ct.lower()).ratio()
            if score >= 0.85:
                return candidate
    except Exception as e:
        print(f"    Title search error: {e}")
    return None


def main():
    papers = storage.load_papers()
    updated = 0

    for paper in papers:
        authors = paper.get("authors") or ""
        if not _is_incomplete(authors):
            continue

        title = (paper.get("title") or "").strip()
        doi = (paper.get("doi") or "").strip()
        print(f"  Resolving: {title[:65]}...")

        hit = None
        if doi:
            hit = _lookup_by_doi(doi)
            if hit:
                print(f"    → found via DOI")
        if not hit:
            hit = _lookup_by_title(title)
            if hit:
                print(f"    → found via title search")

        if not hit:
            print(f"    – not found in Semantic Scholar")
            continue

        new_authors = _fmt_authors(hit.get("authors", []))
        if not new_authors:
            print(f"    – SS returned no authors")
            continue

        paper["authors"] = new_authors

        # Also backfill DOI if missing
        if not doi:
            ext_ids = hit.get("externalIds") or {}
            found_doi = ext_ids.get("DOI") or ""
            if found_doi:
                paper["doi"] = found_doi
                print(f"    ✓ authors + doi")
            else:
                print(f"    ✓ authors")
        else:
            print(f"    ✓ authors")

        updated += 1

    if updated:
        storage.save_papers(papers)
        print(f"\nUpdated {updated} papers with author data.")
    else:
        print("\nNo author updates needed.")


if __name__ == "__main__":
    main()
