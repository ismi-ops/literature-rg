"""Find out whether a preprint has since been published, and where.

Three independent lookups, tried in order (a single hit is enough):
  1. bioRxiv/medRxiv "pubs" API — authoritative for 10.1101/ and 10.64898/ preprints
  2. arXiv API — the <arxiv:doi> element when the authors linked their journal article
  3. Crossref — the `is-preprint-of` relation, which works for any preprint server

lookup_published() returns (info, reliable): info is {"doi", "journal", "year"} or None;
reliable is False when a service errored, so the caller retries next time instead of
recording "checked, not published".
"""
import re
import time
import xml.etree.ElementTree as ET

import requests

from src.title_clean import clean_title

HEADERS = {"User-Agent": "literature-rg/1.0 (preprint status check)"}
TIMEOUT = 20
BIORXIV_PREFIXES = ("10.1101/", "10.64898/")
ARXIV_PREFIX = "10.48550/arxiv."


class ServiceError(Exception):
    """A service failed (network error / 5xx) — the answer is unknown, not 'no'."""


def _get(url: str, params: dict | None = None):
    """GET -> (status_code, response). 404 is a valid 'not found'; anything else non-2xx raises."""
    last = None
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 404:
                return 404, r
            if r.status_code == 429 or r.status_code >= 500:
                last = ServiceError(f"{url} -> HTTP {r.status_code}")
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.status_code, r
        except requests.RequestException as e:
            last = ServiceError(f"{url} -> {type(e).__name__}")
            time.sleep(2 * (attempt + 1))
    raise last


def _clean(doi: str) -> str:
    return re.sub(r"v\d+$", "", (doi or "").strip().lower().replace("https://doi.org/", ""))


def _year(value: str) -> str:
    m = re.match(r"(\d{4})", value or "")
    return m.group(1) if m else ""


def from_biorxiv(doi: str) -> dict | None:
    for server in ("biorxiv", "medrxiv"):
        status, r = _get(f"https://api.biorxiv.org/pubs/{server}/{doi}")
        if status == 404:
            continue
        for item in (r.json().get("collection") or []):
            pub = _clean(item.get("published_doi") or "")
            if pub and pub != doi:
                return {"doi": pub, "journal": item.get("published_journal") or "", "year": _year(item.get("published_date") or "")}
    return None


def from_arxiv(doi: str) -> dict | None:
    arxiv_id = doi[len(ARXIV_PREFIX):]
    status, r = _get("https://export.arxiv.org/api/query", {"id_list": arxiv_id, "max_results": 1})
    if status == 404:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    entry = ET.fromstring(r.text).find("a:entry", ns)
    if entry is None:
        return None
    pub = _clean(entry.findtext("x:doi", "", ns) or "")
    if pub and pub != doi:
        # journal_ref is author-typed free text ("Nature methods, 1-13 (2024)"); Crossref supplies the clean name
        return {"doi": pub, "journal": "", "year": ""}
    return None


def from_crossref(doi: str) -> dict | None:
    status, r = _get(f"https://api.crossref.org/works/{doi}")
    if status == 404:
        return None
    for rel in (((r.json().get("message") or {}).get("relation") or {}).get("is-preprint-of") or []):
        if rel.get("id-type") == "doi" and rel.get("id"):
            return {"doi": _clean(rel["id"]), "journal": "", "year": ""}
    return None


def crossref_details(doi: str) -> dict:
    """Title, journal and year of a DOI (empty strings when Crossref has nothing)."""
    empty = {"title": "", "journal": "", "year": ""}
    try:
        status, r = _get(f"https://api.crossref.org/works/{doi}")
    except ServiceError:
        return dict(empty)
    if status == 404:
        return dict(empty)
    msg = r.json().get("message") or {}
    out = dict(empty)
    out["title"] = clean_title((msg.get("title") or [""])[0])
    out["journal"] = (msg.get("container-title") or [""])[0]
    for field in ("published", "issued", "published-online", "published-print"):
        parts = ((msg.get(field) or {}).get("date-parts") or [[None]])[0]
        if parts and parts[0]:
            out["year"] = str(parts[0])
            break
    return out


def lookup_published(preprint_doi: str):
    """Return (info | None, reliable)."""
    doi = _clean(preprint_doi)
    lookups = []
    if doi.startswith(BIORXIV_PREFIXES):
        lookups.append(from_biorxiv)
    if doi.startswith(ARXIV_PREFIX):
        lookups.append(from_arxiv)
    lookups.append(from_crossref)
    reliable = True
    for fn in lookups:
        try:
            info = fn(doi)
        except ServiceError as e:
            print(f"    {fn.__name__}: {e}")
            reliable = False
            continue
        if info:
            return info, True
    return None, reliable
