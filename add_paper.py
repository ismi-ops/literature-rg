"""
Add a single paper by URL or DOI to papers.json.

Usage:
    python add_paper.py --url https://www.nature.com/articles/...
    python add_paper.py --doi 10.1038/s41467-026-75506-7
"""
import argparse
import re
import sys
import time
from datetime import date

import requests
from dotenv import load_dotenv

from src import storage
from src.relevance import score_and_summarize
from src.sources.pdf_finder import get_pdf_link
from src.sources.semantic_scholar import FIELDS, _normalize

SS_BASE = "https://api.semanticscholar.org/graph/v1"
UNPAYWALL_EMAIL = "isabelle.smith@alleninstitute.org"


# ── Metadata fetchers ──────────────────────────────────────────────────────────

def _doi_from_url(url: str) -> str | None:
    # Standard embedded DOI (e.g. nature.com, doi.org, elifesciences.org)
    m = re.search(r"(10\.\d{4,}/[^\s\"'&?#]+)", url)
    if m:
        return m.group(1).rstrip("/.")

    # Company of Biologists: journals.biologists.com/{journal}/article/…/{article_id}/…
    # e.g. dev205774 → 10.1242/dev.205774, jcs123456 → 10.1242/jcs.123456
    cob = re.search(r"journals\.biologists\.com/[^/]+/article/[^/]+/[^/]+/([a-z]+)(\d+)", url)
    if cob:
        return f"10.1242/{cob.group(1)}.{cob.group(2)}"

    return None


def _fetch_via_ss(doi: str) -> dict | None:
    """Look up metadata from Semantic Scholar by DOI."""
    try:
        resp = requests.get(
            f"{SS_BASE}/paper/DOI:{doi}",
            params={"fields": FIELDS},
            timeout=15,
        )
        time.sleep(0.5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("title"):
                return _normalize(data)
    except Exception as e:
        print(f"  Semantic Scholar lookup failed: {e}")
    return None


def _fetch_via_unpaywall(doi: str) -> dict | None:
    """Fetch basic metadata from Unpaywall (title, authors, year, journal)."""
    try:
        r = requests.get(
            f"https://api.unpaywall.org/v2/{doi.strip()}?email={UNPAYWALL_EMAIL}",
            timeout=10,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        authors_raw = d.get("z_authors") or []
        authors = ", ".join(
            " ".join(filter(None, [a.get("given"), a.get("family")]))
            for a in authors_raw[:8]
        )
        return {
            "title": d.get("title") or "",
            "authors": authors,
            "year": str(d.get("year") or ""),
            "journal": d.get("journal_name") or "",
            "doi": doi,
            "link": d.get("doi_url") or f"https://doi.org/{doi}",
            "abstract": "",
            "tags": [],
            "type": "research",
            "source": "manual",
        }
    except Exception as e:
        print(f"  Unpaywall lookup failed: {e}")
    return None


def fetch_metadata(url: str | None, doi: str | None) -> dict | None:
    """Try to build a paper dict from a URL or DOI."""
    if url and not doi:
        doi = _doi_from_url(url)

    if doi:
        print(f"  DOI detected: {doi}")
        paper = _fetch_via_ss(doi)
        if paper:
            print("  Metadata from Semantic Scholar.")
            return paper
        paper = _fetch_via_unpaywall(doi)
        if paper:
            print("  Metadata from Unpaywall (no abstract — Claude will score on title/journal).")
            return paper

    # Fallback: return a minimal stub with just the URL so the user can fill it in
    if url:
        print("  Could not resolve metadata automatically. Creating stub entry.")
        return {
            "title": url,
            "authors": "",
            "year": str(date.today().year),
            "journal": "",
            "doi": doi or "",
            "link": url,
            "abstract": "",
            "tags": [],
            "type": "research",
            "source": "manual",
        }
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def run(url: str | None = None, doi: str | None = None, min_score: int = 0, dry_run: bool = False):
    load_dotenv()

    print("Fetching paper metadata...")
    paper = fetch_metadata(url, doi)
    if not paper:
        print("Could not fetch metadata. Provide --url or --doi.")
        sys.exit(1)

    print(f"\n  Title  : {paper.get('title', '')[:80]}")
    print(f"  Authors: {str(paper.get('authors', ''))[:60]}")
    print(f"  Journal: {paper.get('journal', '')}  {paper.get('year', '')}")

    print("\nScoring relevance...")
    result = score_and_summarize(paper)
    result["added"] = date.today().isoformat()
    result["curated"] = True
    result["pdf_link"] = get_pdf_link(paper) or ""
    result["source"] = paper.get("source", "manual")

    score = result.get("score", 0)
    print(f"  Score  : {score}/10")
    print(f"  Reason : {result.get('reasoning', '')}")
    if result.get("summary"):
        print(f"  Summary: {result['summary'][:120]}...")

    if dry_run:
        print("\n[DRY RUN] Not writing to papers.json.")
        return

    existing = storage.get_existing_papers()
    doi_key = (result.get("doi") or "").strip().lower()
    title_key = (result.get("title") or "").strip().lower()
    if (doi_key and doi_key in existing) or (title_key and title_key in existing):
        print("\nThis paper is already in papers.json. Nothing added.")
        return

    if score < min_score:
        print(f"\nScore {score} < threshold {min_score}. Not adding (use --min-score 0 to force).")
        return

    added = storage.add_papers([result])
    print(f"\nAdded {added} paper to papers.json.")
    print("Run `python generate_site.py` to regenerate index.html.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a single paper by URL or DOI")
    parser.add_argument("--url", help="Paper landing page URL")
    parser.add_argument("--doi", help="DOI (e.g. 10.1038/...)")
    parser.add_argument("--min-score", type=int, default=0, help="Minimum score to add (default 0 = always add)")
    parser.add_argument("--dry-run", action="store_true", help="Score but don't write")
    args = parser.parse_args()
    if not args.url and not args.doi:
        parser.error("Provide at least --url or --doi")
    run(url=args.url, doi=args.doi, min_score=args.min_score, dry_run=args.dry_run)
