"""PubMed E-utilities client — catches papers in journals Semantic Scholar may index slowly."""
import time
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pubmed(query: str, days_back: int = 14, max_results: int = 10) -> list[dict]:
    """Search PubMed and return normalized paper dicts."""
    mindate = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    maxdate = datetime.now().strftime("%Y/%m/%d")

    params = {
        "db": "pubmed",
        "term": query,
        "datetype": "pdat",
        "mindate": mindate,
        "maxdate": maxdate,
        "retmax": max_results,
        "retmode": "json",
    }

    try:
        resp = requests.get(ESEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        time.sleep(0.4)

        if not ids:
            return []

        return _fetch_papers(ids)
    except Exception as e:
        print(f"  PubMed search error for '{query[:50]}': {e}")
        return []


def _fetch_papers(pmids: list[str]) -> list[dict]:
    try:
        resp = requests.get(
            EFETCH_URL,
            params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
            timeout=60,
        )
        resp.raise_for_status()
        time.sleep(0.4)
        return _parse_pubmed_xml(resp.text)
    except Exception as e:
        print(f"  PubMed fetch error: {e}")
        return []


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    papers = []
    try:
        root = ElementTree.fromstring(xml_text)
        for article in root.findall(".//PubmedArticle"):
            try:
                paper = _parse_article(article)
                if paper:
                    papers.append(paper)
            except Exception:
                continue
    except Exception:
        pass
    return papers


def _parse_article(article) -> dict | None:
    medline = article.find("MedlineCitation")
    if medline is None:
        return None

    art = medline.find("Article")
    if art is None:
        return None

    title_el = art.find("ArticleTitle")
    title = ElementTree.tostring(title_el, encoding="unicode", method="text").strip() if title_el is not None else ""

    abstract_parts = art.findall(".//AbstractText")
    abstract = " ".join((el.text or "") for el in abstract_parts).strip()

    journal_el = art.find(".//Journal/Title")
    journal = journal_el.text or "" if journal_el is not None else ""

    year_el = art.find(".//PubDate/Year")
    year = year_el.text or "" if year_el is not None else ""

    authors = []
    for author in art.findall(".//Author"):
        last = author.find("LastName")
        fore = author.find("ForeName")
        if last is not None and last.text:
            name = f"{fore.text} {last.text}" if fore is not None and fore.text else last.text
            authors.append(name)

    doi = ""
    for id_el in article.findall(".//ArticleId"):
        if id_el.get("IdType") == "doi":
            doi = id_el.text or ""
            break

    pmid_el = medline.find("PMID")
    pmid = pmid_el.text if pmid_el is not None else ""
    url = f"https://doi.org/{doi}" if doi else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "")

    if not title or not abstract:
        return None

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "url": url,
        "abstract": abstract,
        "pub_type": "research",
        "pub_date": "",
        "source": "pubmed",
    }
