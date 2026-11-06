"""People of particular interest — researchers who are not collaborators but whose work we want to see.

The list lives in people_of_interest.json and is used in three places:
  * the agent searches for their new papers (src/config.py adds them to TRACKED_AUTHORS)
  * papers they author get a relevance bonus (src/relevance.py)
  * the site always keeps their names visible on a tile, even when a long author list is collapsed
"""
import json
import re
import unicodedata
from pathlib import Path

PEOPLE_PATH = Path(__file__).parent.parent / "people_of_interest.json"


def load_people(path: Path = PEOPLE_PATH) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    people = data.get("people", []) if isinstance(data, dict) else []
    return [p.strip() for p in people if isinstance(p, str) and p.strip()]


def _tokens(name: str) -> list[str]:
    name = unicodedata.normalize("NFD", name or "")
    name = "".join(c for c in name if not unicodedata.combining(c))
    return [t for t in re.sub(r"[^a-zA-Z\s']", " ", name).lower().replace("-", " ").split() if t]


def _first_names_agree(a: str, b: str) -> bool:
    """Equal, an initial, or a nickname-style prefix ('Jen' / 'Jennifer'); 'Jian' and 'Jane' do not agree."""
    if len(a) == 1 or len(b) == 1:
        return a[0] == b[0]
    short, long_ = sorted((a, b), key=len)
    return long_.startswith(short) and len(short) >= 3


def same_person(a: str, b: str) -> bool:
    """'Michael Elowitz' == 'Michael B. Elowitz' == 'M. Elowitz': same surname, compatible first name."""
    x, y = _tokens(a), _tokens(b)
    return bool(x and y) and x[-1] == y[-1] and _first_names_agree(x[0], y[0])


def _author_names(paper: dict) -> list[str]:
    names = [a.get("name", "") for a in (paper.get("author_data") or []) if isinstance(a, dict)]
    authors = paper.get("authors")
    if isinstance(authors, str):
        names += [n for n in (re.sub(r"\s*et al\.?\s*$", "", s).strip() for s in authors.split(",")) if n]
    elif isinstance(authors, list):
        names += [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors]
    return [n for n in names if n]


def match_paper(paper: dict, people: list[str] | None = None) -> bool:
    """True when any listed person is among the paper's authors."""
    people = load_people() if people is None else people
    if not people:
        return False
    return any(same_person(n, p) for n in _author_names(paper) for p in people)
