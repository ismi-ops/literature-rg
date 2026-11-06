"""Allen Institute for Cell Science's own publications — the agent should not suggest these.

The list lives in own_publications.json (refreshed by update_own_publications.py).
A paper counts as ours when its DOI is on the list or its title matches a listed title.
"""
import difflib
import json
import re
from pathlib import Path

OWN_PATH = Path(__file__).parent.parent / "own_publications.json"
FUZZY_RATIO = 0.93   # tolerates punctuation/subtitle drift between a preprint and its published title
MIN_FUZZY_LEN = 25   # never fuzzy-match very short titles


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def normalize_doi(doi: str) -> str:
    doi = (doi or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)


class OwnPublications:
    def __init__(self, entries: list[dict]):
        self.dois = {normalize_doi(e["doi"]) for e in entries if e.get("doi")}
        self.titles = {normalize_title(e["title"]) for e in entries if e.get("title")} - {""}

    def match(self, paper: dict, fuzzy: bool = True) -> bool:
        doi = normalize_doi(paper.get("doi") or "")
        if doi and doi in self.dois:
            return True
        title = normalize_title(paper.get("title") or "")
        if not title:
            return False
        if title in self.titles:
            return True
        if fuzzy and len(title) >= MIN_FUZZY_LEN:
            for own in self.titles:
                if len(own) >= MIN_FUZZY_LEN and abs(len(own) - len(title)) <= 40:
                    s = difflib.SequenceMatcher(None, title, own)
                    if s.real_quick_ratio() >= FUZZY_RATIO and s.quick_ratio() >= FUZZY_RATIO and s.ratio() >= FUZZY_RATIO:
                        return True
        return False


def load_entries(path: Path = OWN_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("publications", []) if isinstance(data, dict) else []


def load(path: Path = OWN_PATH) -> OwnPublications:
    return OwnPublications(load_entries(path))
