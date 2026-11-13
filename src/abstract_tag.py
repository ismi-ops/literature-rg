"""Spot conference abstracts, which look like papers in the databases but are one-page meeting submissions.

Signals (any one is enough):
  * the title starts with "Abstract ..." / a session code ("O-243", "P5-06-02", "CNSC-31.")
  * the DOI belongs to a prefix that only publishes meeting abstracts (AACR proceedings, FASEB, ASH)
  * the journal name says Abstracts / Supplement / Proceedings of a meeting
  * a Fertility and Sterility (ASRM) supplement item: DOI 10.1016/j.fertnstert and an ALL-CAPS title
"""
import re

_SESSION_CODE = re.compile(r"^\s*(abstract\b|poster\b|[A-Z]{1,5}-?\d{1,3}(-\d+)*\s*[:.]\s)", re.I)
_ABSTRACT_DOI = ("10.1158/1538-7445", "10.1096/fasebj", "10.1182/blood-")
_JOURNAL = re.compile(r"\b(abstracts?|supplement|meeting|congress|conference)\b", re.I)


def is_conference_abstract(paper: dict) -> bool:
    title = (paper.get("title") or "").strip()
    doi = (paper.get("doi") or "").strip().lower()
    journal = paper.get("journal") or ""
    if _SESSION_CODE.match(title):
        return True
    if doi.startswith(_ABSTRACT_DOI):
        return True
    if journal and _JOURNAL.search(journal) and not paper.get("preprint"):
        return True
    if doi.startswith("10.1016/j.fertnstert") and title.isupper():
        return True
    return False
