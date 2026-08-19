"""Semantic Scholar API client — primary paper discovery source."""
import time
import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,publicationDate,venue,externalIds,abstract,url,publicationTypes,s2FieldsOfStudy"


def search_papers(query: str, days_back: int = 14, limit: int = 10) -> list[dict]:
    """Search Semantic Scholar for recent papers matching the query."""
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "query": query,
        "fields": FIELDS,
        "limit": limit,
        "publicationDateOrYear": f"{cutoff}:",
    }
    try:
        resp = requests.get(f"{BASE_URL}/paper/search", params=params, timeout=30)
        resp.raise_for_status()
        papers = resp.json().get("data", [])
        time.sleep(1.2)  # Stay within free-tier rate limit
        return [_normalize(p) for p in papers if p.get("abstract")]
    except Exception as e:
        print(f"  SS search error for '{query[:50]}': {e}")
        return []


def get_author_papers(author_name: str, days_back: int = 14) -> list[dict]:
    """Fetch recent papers by a tracked author."""
    try:
        resp = requests.get(
            f"{BASE_URL}/author/search",
            params={"query": author_name, "fields": "authorId,name"},
            timeout=30,
        )
        resp.raise_for_status()
        authors = resp.json().get("data", [])
        time.sleep(1.0)

        if not authors:
            return []

        author_id = authors[0]["authorId"]
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        resp = requests.get(
            f"{BASE_URL}/author/{author_id}/papers",
            params={"fields": FIELDS, "limit": 8},
            timeout=30,
        )
        resp.raise_for_status()
        papers = resp.json().get("data", [])
        time.sleep(1.0)

        recent = []
        for p in papers:
            pub_date = p.get("publicationDate", "") or ""
            if pub_date >= cutoff and p.get("abstract"):
                recent.append(_normalize(p))
        return recent

    except Exception as e:
        print(f"  SS author error for '{author_name}': {e}")
        return []


def _normalize(paper: dict) -> dict:
    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI", "")

    url = paper.get("url", "") or ""
    if doi and not url:
        url = f"https://doi.org/{doi}"

    pub_types = paper.get("publicationTypes") or []
    pub_type = "research"
    if "Review" in pub_types:
        pub_type = "review"
    elif any(t in pub_types for t in ("Comment", "Editorial", "LettersAndComments")):
        pub_type = "perspective"

    fos = paper.get("s2FieldsOfStudy") or []
    publisher_keywords = list({f["category"] for f in fos if f.get("category")})

    return {
        "title": paper.get("title", ""),
        "authors": [a.get("name", "") for a in (paper.get("authors") or [])],
        "year": str(paper.get("year", "")) if paper.get("year") else "",
        "journal": paper.get("venue", ""),
        "doi": doi,
        "url": url,
        "abstract": paper.get("abstract", ""),
        "pub_type": pub_type,
        "pub_date": paper.get("publicationDate", "") or "",
        "publisher_keywords": publisher_keywords,
        "source": "semantic_scholar",
    }
