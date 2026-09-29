"""
Add a single paper or article by URL, DOI, or manual title to papers.json.

Usage:
    python add_paper.py --url https://www.nature.com/articles/...
    python add_paper.py --doi 10.1038/s41467-026-75506-7
    python add_paper.py --title "Connecting tissue physical changes..." --url https://www.embl.org/... --type article
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
        doi = m.group(1).rstrip("/.")
        # Strip biorxiv/medrxiv version suffixes: e.g. 10.1101/2022.09.02.506324v2
        doi = re.sub(r"v\d+(?:\.\w+)*$", "", doi)
        return doi

    # Company of Biologists: journals.biologists.com/{journal}/article/…/{article_id}/…
    # e.g. dev205774 → 10.1242/dev.205774, jcs123456 → 10.1242/jcs.123456
    cob = re.search(r"journals\.biologists\.com/[^/]+/article/[^/]+/[^/]+/([a-z]+)(\d+)", url)
    if cob:
        return f"10.1242/{cob.group(1)}.{cob.group(2)}"

    return None


def _arxiv_id_from_url(url: str) -> str | None:
    """Return bare arxiv ID (e.g. '2609.21021') from an arxiv URL, or None."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d+)", url)
    return m.group(1) if m else None


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


def _fetch_via_ss_arxiv(arxiv_id: str) -> dict | None:
    """Look up an arxiv preprint from Semantic Scholar using its arxiv ID."""
    try:
        resp = requests.get(
            f"{SS_BASE}/paper/arXiv:{arxiv_id}",
            params={"fields": FIELDS},
            timeout=15,
        )
        time.sleep(0.5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("title"):
                paper = _normalize(data)
                # Ensure the canonical arxiv DOI is set
                if not paper.get("doi"):
                    paper["doi"] = f"10.48550/arXiv.{arxiv_id}"
                return paper
    except Exception as e:
        print(f"  Semantic Scholar (arXiv) lookup failed: {e}")
    return None


def _fetch_via_arxiv_api(arxiv_id: str) -> dict | None:
    """Fetch metadata directly from the arxiv Atom API — works for brand-new preprints."""
    try:
        resp = requests.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": arxiv_id, "max_results": 1},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        # Parse Atom XML — avoid lxml dependency, use stdlib ElementTree
        import xml.etree.ElementTree as ET
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(resp.text)
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
        abstract = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")
        published = (entry.findtext("atom:published", "", ns) or "")[:4]  # year
        authors = ", ".join(
            (a.findtext("atom:name", "", ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        )[:8 * 30]  # rough cap
        if not title:
            return None
        return {
            "title": title,
            "authors": authors,
            "year": published,
            "journal": "arXiv",
            "doi": f"10.48550/arXiv.{arxiv_id}",
            "link": f"https://arxiv.org/abs/{arxiv_id}",
            "abstract": abstract,
            "tags": [],
            "type": "research",
            "source": "manual",
        }
    except Exception as e:
        print(f"  arXiv API lookup failed: {e}")
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
    # Check for arxiv URL before the generic DOI extractor
    if url and not doi:
        arxiv_id = _arxiv_id_from_url(url)
        if arxiv_id:
            print(f"  arXiv ID detected: {arxiv_id}")
            paper = _fetch_via_ss_arxiv(arxiv_id)
            if paper:
                print("  Metadata from Semantic Scholar (arXiv).")
                return paper
            paper = _fetch_via_arxiv_api(arxiv_id)
            if paper:
                print("  Metadata from arXiv API.")
                return paper
        doi = _doi_from_url(url)

    if doi:
        print(f"  DOI detected: {doi}")
        # arxiv DOIs (10.48550/arXiv.*) work better via the arXiv SS endpoint
        arxiv_match = re.match(r"10\.48550/arXiv\.(\d{4}\.\d+)", doi, re.IGNORECASE)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            paper = _fetch_via_ss_arxiv(arxiv_id)
            if paper:
                print("  Metadata from Semantic Scholar (arXiv).")
                return paper
            paper = _fetch_via_arxiv_api(arxiv_id)
            if paper:
                print("  Metadata from arXiv API.")
                return paper
        paper = _fetch_via_ss(doi)
        if paper:
            print("  Metadata from Semantic Scholar.")
            return paper
        paper = _fetch_via_unpaywall(doi)
        if paper:
            print("  Metadata from Unpaywall (no abstract — Claude will score on title/journal).")
            return paper

    # Could not resolve — fail with a helpful message rather than saving a useless stub.
    # News articles, blog posts, and non-paper URLs won't have DOIs or SS entries.
    if url:
        print(
            "\n  Could not resolve paper metadata from this URL.\n"
            "  If this is a news article or blog post, use --title to provide the\n"
            "  title manually and --type article (or omit --doi).\n"
        )
        sys.exit(1)
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def run(url: str | None = None, doi: str | None = None, title: str | None = None,
        content_type: str = "research", min_score: int = 0, dry_run: bool = False):
    load_dotenv()

    if title:
        # Manual entry for news articles / non-DOI content
        paper = {
            "title": title,
            "authors": "",
            "year": str(date.today().year),
            "journal": "",
            "doi": doi or "",
            "link": url or "",
            "abstract": "",
            "tags": [],
            "type": content_type,
            "source": "manual",
        }
        print(f"  Manual entry: {title[:80]}")
    else:
        print("Fetching paper metadata...")
        paper = fetch_metadata(url, doi)
        if not paper:
            print("Could not fetch metadata. Provide --url, --doi, or --title.")
            sys.exit(1)
        paper["type"] = content_type

    print(f"\n  Title  : {paper.get('title', '')[:80]}")
    print(f"  Authors: {str(paper.get('authors', ''))[:60]}")
    print(f"  Journal: {paper.get('journal', '')}  {paper.get('year', '')}")

    print("\nScoring relevance...")
    result = score_and_summarize(paper)
    result["added"] = date.today().isoformat()
    result["curated"] = True
    result["pdf_link"] = get_pdf_link(paper) or ""
    result["source"] = paper.get("source", "manual")

    _preprint_hosts = ("biorxiv.org", "medrxiv.org", "arxiv.org", "preprints.org", "10.1101/", "10.48550/")
    link_or_doi = (url or "") + (doi or "") + (result.get("doi") or "")
    if any(h in link_or_doi for h in _preprint_hosts):
        result["preprint"] = True

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
    parser = argparse.ArgumentParser(description="Add a single paper or article by URL, DOI, or title")
    parser.add_argument("--url", help="Paper/article URL")
    parser.add_argument("--doi", help="DOI (e.g. 10.1038/...)")
    parser.add_argument("--title", help="Title for manual entry (news articles, blog posts, etc.)")
    parser.add_argument("--type", dest="content_type", default="research",
                        choices=["research", "review", "perspective", "article"],
                        help="Content type (default: research)")
    parser.add_argument("--min-score", type=int, default=0, help="Minimum score to add (default 0 = always add)")
    parser.add_argument("--dry-run", action="store_true", help="Score but don't write")
    args = parser.parse_args()
    if not args.url and not args.doi and not args.title:
        parser.error("Provide at least --url, --doi, or --title")
    run(url=args.url, doi=args.doi, title=args.title, content_type=args.content_type,
        min_score=args.min_score, dry_run=args.dry_run)
