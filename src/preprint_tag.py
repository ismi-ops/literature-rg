"""Is a paper a bioRxiv / medRxiv preprint? Used so every way a paper gets in (agent, author tracker,
Add Paper) tags them the same way.

DOI prefixes: bioRxiv/medRxiv used 10.1101/<yyyy.mm.dd.number> and now 10.64898/. The 10.1101/ prefix is
also shared with Cold Spring Harbor *journals* (Genes & Development, Genome Research, ...), whose DOIs look
like 10.1101/gad.123456 - those are not preprints, so the dated pattern is required.
"""
import re

_DATED = re.compile(r"^10\.1101/\d{4}\.\d{2}\.\d{2}\.\d+")
_SERVERS = ("biorxiv", "medrxiv")


def _is_server(text: str) -> bool:
    t = (text or "").lower()
    return any(s in t for s in _SERVERS)


def is_biorxiv_preprint(paper: dict) -> bool:
    doi = (paper.get("doi") or "").strip().lower().replace("https://doi.org/", "")
    journal = (paper.get("journal") or "").strip()
    link = paper.get("link") or paper.get("url") or ""
    if doi:
        if not (_DATED.match(doi) or doi.startswith("10.64898/")):
            return False   # a journal DOI, whatever the stored journal name says
        # A bioRxiv DOI on a tile whose venue is a real journal is a published record that kept the old DOI.
        return not journal or _is_server(journal) or _is_server(link)
    return _is_server(journal) or _is_server(link)
