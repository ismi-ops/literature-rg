"""Fetch a paper's abstract by DOI (OpenAlex first, Semantic Scholar as a fallback)."""
import re
import time

import requests

HEADERS = {"User-Agent": "literature-rg/1.0 (abstract backfill)"}
TIMEOUT = 20


def _get(url: str, params: dict | None = None) -> dict | None:
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def rebuild_inverted_index(inv: dict | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; put the words back in order."""
    if not inv:
        return ""
    slots = {}
    for word, positions in inv.items():
        for pos in positions:
            slots[pos] = word
    return " ".join(slots[i] for i in sorted(slots))


def from_openalex(doi: str) -> str:
    data = _get(f"https://api.openalex.org/works/https://doi.org/{doi}")
    return rebuild_inverted_index((data or {}).get("abstract_inverted_index"))


def from_semantic_scholar(doi: str) -> str:
    data = _get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}", {"fields": "abstract"})
    return ((data or {}).get("abstract") or "").strip()


def fetch_abstract(doi: str) -> str:
    """Best abstract found for the DOI, or '' (too-short results are treated as 'not found')."""
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip())
    if not doi:
        return ""
    for fn in (from_openalex, from_semantic_scholar):
        text = fn(doi)
        if len(text.split()) >= 25:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
        time.sleep(0.3)
    return ""
