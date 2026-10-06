"""
VIP author tracking via Semantic Scholar.

Resolves author SS IDs (cached in authors.json), then fetches recent papers.
Each paper gets vip_author set; papers below the score threshold also get
vip_only=True so they are hidden from the main feed.
"""
import json
import re
import time
from pathlib import Path

import requests

SS_BASE = "https://api.semanticscholar.org/graph/v1"
AUTHORS_PATH = Path(__file__).parent.parent.parent / "authors.json"

PAPER_FIELDS = (
    "title,authors,year,publicationDate,journal,externalIds,"
    "abstract,citationCount,openAccessPdf,publicationTypes"
)


def _ss_get(url: str, params: dict | None = None, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20,
                             headers={"User-Agent": "literature-rg/1.0"})
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code == 200:
                return r.json()
            return None
        except Exception as e:
            print(f"  SS request error ({url}): {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


def _resolve_author_id(author: dict) -> str | None:
    """Search SS for an author by name and pick the best match."""
    query = author["search_name"]
    institution = author.get("institution", "")
    data = _ss_get(f"{SS_BASE}/author/search", {
        "query": query,
        "fields": "authorId,name,affiliations,paperCount",
        "limit": 5,
    })
    time.sleep(0.5)
    if not data or not data.get("data"):
        return None

    candidates = data["data"]
    # Prefer candidate whose affiliation matches, else take highest paperCount
    if institution:
        inst_lower = institution.lower()
        for c in candidates:
            affs = [a.get("name", "").lower() for a in (c.get("affiliations") or [])]
            if any(inst_lower in a or a in inst_lower for a in affs):
                return c["authorId"]

    # Fall back to first result (highest relevance by SS)
    return candidates[0]["authorId"] if candidates else None


def load_authors() -> list[dict]:
    with open(AUTHORS_PATH) as f:
        return json.load(f)


def save_authors(authors: list[dict]) -> None:
    with open(AUTHORS_PATH, "w") as f:
        json.dump(authors, f, indent=2, ensure_ascii=False)
        f.write("\n")


def resolve_all_ids(authors: list[dict]) -> list[dict]:
    """Fill in missing ss_id fields and save back to authors.json."""
    changed = False
    for author in authors:
        if author.get("ss_id"):
            continue
        print(f"  Resolving SS ID for {author['name']}...")
        ss_id = _resolve_author_id(author)
        if ss_id:
            author["ss_id"] = ss_id
            print(f"    → {ss_id}")
            changed = True
        else:
            print(f"    → not found")
        time.sleep(1)
    if changed:
        save_authors(authors)
    return authors


def _normalize_paper(raw: dict, vip_author_name: str) -> dict | None:
    """Convert a SS paper record to our paper dict format."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None

    ext = raw.get("externalIds") or {}
    doi = (ext.get("DOI") or "").strip()
    arxiv_id = ext.get("ArXiv") or ""

    authors_list = raw.get("authors") or []
    authors_str = ", ".join(a.get("name", "") for a in authors_list[:8])

    pub_date = raw.get("publicationDate") or ""
    year = pub_date[:4] if pub_date else str(raw.get("year") or "")

    journal_obj = raw.get("journal") or {}
    journal = journal_obj.get("name") or ""
    if not journal:
        pub_types = raw.get("publicationTypes") or []
        journal = ", ".join(pub_types) if pub_types else ""

    link = ""
    if doi:
        link = f"https://doi.org/{doi}"
    elif arxiv_id:
        link = f"https://arxiv.org/abs/{arxiv_id}"

    pdf_link = ""
    oa = raw.get("openAccessPdf") or {}
    if oa.get("url"):
        pdf_link = oa["url"]

    preprint = bool(arxiv_id) or any(h in doi for h in ("10.1101/", "10.48550/"))

    content_type = "research"
    pub_types = raw.get("publicationTypes") or []
    if "Review" in pub_types:
        content_type = "review"

    return {
        "title": title,
        "authors": authors_str,
        "year": year,
        "journal": journal,
        "doi": doi,
        "link": link,
        "abstract": (raw.get("abstract") or "").strip(),
        "tags": [],
        "type": content_type,
        "source": "author_tracker",
        "vip_author": vip_author_name,
        "preprint": preprint,
        "pdf_link": pdf_link,
    }


def fetch_recent_papers(author: dict, since_date: str, limit: int = 20) -> list[dict]:
    """Fetch papers published on or after since_date (YYYY-MM-DD) for one author."""
    ss_id = author.get("ss_id")
    if not ss_id:
        return []

    data = _ss_get(
        f"{SS_BASE}/author/{ss_id}/papers",
        {
            "fields": PAPER_FIELDS,
            "limit": limit,
            "sort": "publicationDate:desc",
        },
    )
    time.sleep(0.5)
    if not data or not data.get("data"):
        return []

    papers = []
    for raw in data["data"]:
        pub_date = raw.get("publicationDate") or ""
        if pub_date and pub_date < since_date:
            break  # results are sorted newest-first; stop when too old
        paper = _normalize_paper(raw, author["name"])
        if paper:
            papers.append(paper)
    return papers


def fetch_all_recent(since_date: str) -> list[dict]:
    """Load authors, resolve IDs, fetch recent papers from all VIP authors."""
    authors = load_authors()
    authors = resolve_all_ids(authors)

    all_papers: list[dict] = []
    for author in authors:
        if not author.get("ss_id"):
            print(f"  Skipping {author['name']} (no SS ID resolved)")
            continue
        print(f"  Fetching papers for {author['name']}...")
        papers = fetch_recent_papers(author, since_date)
        print(f"    → {len(papers)} recent paper(s)")
        all_papers.extend(papers)

    return all_papers
