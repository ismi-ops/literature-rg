"""bioRxiv API client — catches preprints before they're indexed by Semantic Scholar."""
import time
import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.biorxiv.org"

CATEGORIES_OF_INTEREST = {
    "cell biology",
    "developmental biology",
    "synthetic biology",
    "biophysics",
    "systems biology",
}


def fetch_recent(days_back: int = 14, server: str = "biorxiv") -> list[dict]:
    """Fetch recent preprints in biology-relevant categories."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    papers = []
    cursor = 0
    max_papers = 300

    while cursor < max_papers:
        url = f"{BASE_URL}/details/{server}/{start_date}/{end_date}/{cursor}/json"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            time.sleep(0.5)

            collection = data.get("collection", [])
            if not collection:
                break

            for p in collection:
                cat = p.get("category", "").lower()
                if any(interest in cat for interest in CATEGORIES_OF_INTEREST):
                    papers.append(_normalize(p))

            messages = data.get("messages", [{}])
            total = messages[0].get("total", 0) if messages else 0
            cursor += len(collection)
            if cursor >= total:
                break

        except Exception as e:
            print(f"  bioRxiv error at cursor {cursor}: {e}")
            break

    return papers


def _normalize(p: dict) -> dict:
    doi = p.get("doi", "")
    url = f"https://www.biorxiv.org/content/{doi}v1" if doi else ""

    raw_authors = p.get("authors", "")
    authors = [a.strip() for a in raw_authors.split(";") if a.strip()]

    return {
        "title": p.get("title", ""),
        "authors": authors,
        "year": (p.get("date", "") or "")[:4],
        "journal": "bioRxiv",
        "doi": doi,
        "url": url,
        "abstract": p.get("abstract", ""),
        "pub_type": "research",
        "pub_date": p.get("date", "") or "",
        "source": "biorxiv",
    }
