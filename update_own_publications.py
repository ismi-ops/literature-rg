"""Refresh own_publications.json — the list of Allen Institute for Cell Science papers the agent skips.

Sources (merged, never shrinking):
  * PubMed: every record with "Allen Institute for Cell Science" in an author affiliation
  * the institute's publications page (best effort: titles and DOIs found in its HTML)
  * manual entries already in the file (marked "source": "manual") are always kept

Usage:
    python update_own_publications.py              # refresh the list
    python update_own_publications.py --dry-run    # show what would change
    python update_own_publications.py --prune      # also reject matching papers already in papers.json
"""
import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date

import requests

from src import storage
from src.own_publications import OWN_PATH, OwnPublications, load_entries, normalize_doi, normalize_title

HEADERS = {"User-Agent": "literature-rg/1.0 (own-publications list)"}
PUBMED_TERM = '"Allen Institute for Cell Science"[Affiliation]'
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
WEBSITE_URL = "https://alleninstitute.org/publications?publications_accelerator_equal=Cell+Science"
TIMEOUT = 30


def fetch_pubmed() -> list[dict]:
    r = requests.get(f"{EUTILS}/esearch.fcgi", headers=HEADERS, timeout=TIMEOUT,
                     params={"db": "pubmed", "term": PUBMED_TERM, "retmax": 1000, "retmode": "json"})
    r.raise_for_status()
    ids = r.json()["esearchresult"]["idlist"]
    return parse_pubmed_batches(ids)


def parse_pubmed_batches(ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 100):
        r = requests.post(f"{EUTILS}/efetch.fcgi", headers=HEADERS, timeout=TIMEOUT,
                          data={"db": "pubmed", "id": ",".join(ids[i:i + 100]), "retmode": "xml"})
        r.raise_for_status()
        out.extend(parse_pubmed_xml(r.text))
    return out


def parse_pubmed_xml(xml_text: str) -> list[dict]:
    out = []
    for art in ET.fromstring(xml_text).iter("PubmedArticle"):
        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        doi = ""
        for aid in art.iter("ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                doi = aid.text.strip()
        if title:
            out.append({"title": title.rstrip("."), "doi": doi, "source": "pubmed"})
    return out


def parse_website(page: str) -> list[dict]:
    """Only entries tied to a DOI link count: a live run showed that headings and menu text on the page are
    noise (the publication list itself appears to be loaded by JavaScript, so a plain fetch may find nothing)."""
    out, seen = [], set()
    for m in re.finditer(r"""<a\b[^>]*href=["'][^"']*doi\.org/(10\.\d{4,9}/[^"'\s?#]+)[^"']*["'][^>]*>(.*?)</a>""", page, flags=re.S | re.I):
        doi = normalize_doi(m.group(1)).rstrip(".,;)")
        if doi in seen:
            continue
        seen.add(doi)
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        text = re.sub(r"\s+", " ", text).strip().rstrip(".")
        title = text if len(text) >= 30 and len(text.split()) >= 5 else ""   # "Read more" etc. are not titles
        out.append({"title": title, "doi": doi, "source": "website"})
    return out


def fetch_website() -> list[dict]:
    r = requests.get(WEBSITE_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_website(r.text)


def merge(existing: list[dict], fetched: list[dict]) -> list[dict]:
    """Union by DOI / normalized title; manual entries and earlier entries are never dropped."""
    merged, by_doi, by_title = [], {}, {}
    for e in existing + fetched:
        doi, title = normalize_doi(e.get("doi") or ""), normalize_title(e.get("title") or "")
        hit = (by_doi.get(doi) if doi else None) or (by_title.get(title) if title else None)
        if hit is not None:
            for k in ("title", "doi"):
                if not hit.get(k) and e.get(k):
                    hit[k] = e[k]
            if doi:
                by_doi[doi] = hit
            if title:
                by_title[title] = hit
            continue
        entry = {k: e[k] for k in ("title", "doi", "source") if e.get(k)}
        merged.append(entry)
        if doi:
            by_doi[doi] = entry
        if title:
            by_title[title] = entry
    return merged


def prune(papers: list[dict], own: OwnPublications) -> list[str]:
    """Reject papers already in papers.json that are ours. Exact matches only, and never papers that
    were added by hand (curated) or sent by Ru."""
    removed = []
    for p in papers:
        if p.get("rejected") or p.get("ru_pick") or p.get("curated"):
            continue
        if own.match(p, fuzzy=False):
            p["rejected"] = True
            removed.append(p.get("title", "")[:90])
    return removed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune", action="store_true")
    args = ap.parse_args()

    existing = load_entries()
    fetched, pubmed_failed = [], False
    for name, fn in (("PubMed", fetch_pubmed), ("website", fetch_website)):
        try:
            got = fn()
            print(f"{name}: {len(got)} entries")
            for e in got[:8]:   # a peek, so a bad parse is obvious in the log
                print(f"    - {(e.get('title') or e.get('doi'))[:100]}")
            fetched.extend(got)
        except Exception as e:   # one source failing must not wipe or block the other
            pubmed_failed = pubmed_failed or name == "PubMed"
            print(f"{name}: FAILED ({type(e).__name__}: {e})")
    if not fetched:
        sys.exit("No source returned anything; leaving own_publications.json unchanged.")

    merged = merge(existing, fetched)
    print(f"List: {len(existing)} -> {len(merged)} entries")
    if not args.dry_run and len(merged) != len(existing):
        OWN_PATH.write_text(json.dumps({"updated": date.today().isoformat(), "publications": merged},
                                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.prune:
        papers = storage.load_papers()
        removed = prune(papers, OwnPublications(merged))
        print(f"Pruned {len(removed)} paper(s) already in papers.json:")
        for t in removed:
            print("  -", t)
        if removed and not args.dry_run:
            storage.save_papers(papers)
    sys.exit(1 if pubmed_failed else 0)   # a red run means the main source needs attention


if __name__ == "__main__":
    main()
