"""Find open-access PDF links for papers via Unpaywall and known URL patterns."""
import re
import time
import requests

_UNPAYWALL_EMAIL = "isabelle.smith@alleninstitute.org"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "literature-rg/1.0 (mailto:isabelle.smith@alleninstitute.org)"


def _biorxiv_pdf(link: str) -> str | None:
    link = link.rstrip("/")
    link = re.sub(r"\.full$", "", link)
    if "biorxiv.org/content/" in link or "medrxiv.org/content/" in link:
        return link + ".full.pdf"
    return None


def _unpaywall_pdf(doi: str) -> str | None:
    if not doi:
        return None
    url = f"https://api.unpaywall.org/v2/{doi.strip()}?email={_UNPAYWALL_EMAIL}"
    try:
        r = _SESSION.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        loc = data.get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url") or None
    except Exception:
        return None


def get_pdf_link(paper: dict) -> str | None:
    """Return a free PDF URL for a paper, or None if not available."""
    link = paper.get("link") or paper.get("url") or ""
    doi = paper.get("doi") or ""

    if "biorxiv.org" in link or "medrxiv.org" in link:
        return _biorxiv_pdf(link)

    if doi:
        time.sleep(0.5)
        return _unpaywall_pdf(doi)

    doi_match = re.search(r"10\.\d{4,}/[^\s\"'&?]+", link)
    if doi_match:
        time.sleep(0.5)
        return _unpaywall_pdf(doi_match.group())

    return None
