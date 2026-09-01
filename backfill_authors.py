"""
Backfill missing or incomplete author lists.

Tries CrossRef first (DOI-based, provides ORCID IDs), then falls back to
Semantic Scholar by DOI, then by title. Updates authors and fills in any
missing DOIs in the process. Stores author_data with ORCID IDs when available.

Incomplete detection covers: blank, last-name-only, initial-only first names
(e.g. "I. Zorzan"), et al. abbreviations, "Multiple authors", and "&"-joined
last names.
"""
import re
import time
import requests
from difflib import SequenceMatcher
from src import storage

SS_BASE = "https://api.semanticscholar.org/graph/v1"
CR_BASE = "https://api.crossref.org/works"
MAILTO = "isabelle.smith@alleninstitute.org"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "literature-rg/1.0 (mailto:isabelle.smith@alleninstitute.org)"

SS_AUTHOR_FIELDS = "paperId,title,authors,externalIds,publicationDate,year"
_INITIAL_RE = re.compile(r"^[A-Z]\.$")


def _fmt_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) > 8:
        return ", ".join(names[:8]) + " et al."
    return ", ".join(names)


def _extract_orcid(val: str) -> str:
    """Return the bare ORCID identifier from a URL or plain ID string."""
    if not val:
        return ""
    m = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", val)
    return m.group(1) if m else ""


def _is_incomplete(authors: str) -> bool:
    """True when the authors string is blank, abbreviated, or uses initials / last names only."""
    if not authors or not authors.strip():
        return True
    s = authors.strip()
    if s.lower() in ("multiple authors", "multiple"):
        return True
    if "et al." in s.lower() or " et al" in s.lower():
        return True
    # Normalise "&" → "," so "Nunes & Barriga" splits into two parts
    s_norm = re.sub(r"\s*&\s*", ", ", s)
    parts = [p.strip() for p in s_norm.split(",") if p.strip()]
    if not parts:
        return True
    for part in parts:
        words = part.split()
        if not words:
            continue
        if len(words) == 1:          # last-name only
            return True
        if _INITIAL_RE.match(words[0]):   # first-name initial like "I. Zorzan"
            return True
    return False


# ── CrossRef ────────────────────────────────────────────────────────────────

def _crossref_by_doi(doi: str) -> dict | None:
    """Return {'names': [...], 'author_data': [{name, orcid?}, ...]} or None."""
    try:
        r = _SESSION.get(
            f"{CR_BASE}/{doi}",
            params={"mailto": MAILTO},
            timeout=15,
        )
        time.sleep(0.3)
        if r.status_code != 200:
            return None
        raw = r.json().get("message", {}).get("author", [])
        names, author_data = [], []
        for a in raw:
            given = (a.get("given") or "").strip()
            family = (a.get("family") or "").strip()
            name = (f"{given} {family}".strip()) if given else family
            if not name:
                continue
            names.append(name)
            entry: dict = {"name": name}
            orcid = _extract_orcid(a.get("ORCID") or "")
            if orcid:
                entry["orcid"] = orcid
            author_data.append(entry)
        if names:
            return {"names": names, "author_data": author_data}
    except Exception as e:
        print(f"    CrossRef error: {e}")
    return None


# ── Semantic Scholar ─────────────────────────────────────────────────────────

def _ss_by_doi(doi: str) -> dict | None:
    try:
        r = _SESSION.get(
            f"{SS_BASE}/paper/DOI:{doi}",
            params={"fields": SS_AUTHOR_FIELDS},
            timeout=15,
        )
        time.sleep(0.5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    SS DOI error: {e}")
    return None


def _ss_by_title(title: str) -> dict | None:
    try:
        r = _SESSION.get(
            f"{SS_BASE}/paper/search",
            params={"query": title, "fields": SS_AUTHOR_FIELDS, "limit": 3},
            timeout=15,
        )
        time.sleep(0.5)
        if r.status_code != 200:
            return None
        for candidate in r.json().get("data", []):
            ct = candidate.get("title") or ""
            if SequenceMatcher(None, title.lower(), ct.lower()).ratio() >= 0.85:
                return candidate
    except Exception as e:
        print(f"    SS title error: {e}")
    return None


def _fmt_ss_authors(ss_authors: list) -> str:
    return _fmt_names([a["name"] for a in ss_authors if a.get("name")])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    papers = storage.load_papers()
    updated = 0

    for paper in papers:
        if not _is_incomplete(paper.get("authors") or ""):
            continue

        title = (paper.get("title") or "").strip()
        doi = (paper.get("doi") or "").strip()
        print(f"  Resolving: {title[:65]}...")

        # 1. CrossRef (best for DOI lookups; returns ORCID)
        if doi:
            cr = _crossref_by_doi(doi)
            if cr:
                print("    → CrossRef")
                paper["authors"] = _fmt_names(cr["names"])
                paper["author_data"] = cr["author_data"]
                updated += 1
                print("    ✓ authors" + (" + orcid" if any(e.get("orcid") for e in cr["author_data"]) else ""))
                continue

        # 2. Semantic Scholar by DOI
        hit = None
        if doi:
            hit = _ss_by_doi(doi)
            if hit:
                print("    → Semantic Scholar (DOI)")
        # 3. Semantic Scholar by title
        if not hit:
            hit = _ss_by_title(title)
            if hit:
                print("    → Semantic Scholar (title)")

        if not hit:
            print("    – not found")
            continue

        new_authors = _fmt_ss_authors(hit.get("authors", []))
        if not new_authors:
            print("    – no authors returned")
            continue

        paper["authors"] = new_authors
        if not doi:
            found_doi = (hit.get("externalIds") or {}).get("DOI") or ""
            if found_doi:
                paper["doi"] = found_doi
                print("    ✓ authors + doi")
            else:
                print("    ✓ authors")
        else:
            print("    ✓ authors")
        updated += 1

    if updated:
        storage.save_papers(papers)
        print(f"\nUpdated {updated} papers.")
    else:
        print("\nNo author updates needed.")


if __name__ == "__main__":
    main()
