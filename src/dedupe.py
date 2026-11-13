"""Find tiles that are the same paper.

Kinds:
  version-doi    same eLife article under its versioned DOI (10.7554/elife.91422.3 vs 10.7554/eLife.91422)
  preprint-twin  a preprint (or conference abstract) tile and its published article (same/near-identical title, preprint no later than the article)
  preprint-pair  the same preprint listed twice (e.g. a bioRxiv DOI tile and an arXiv tile without a DOI)
  possible-twin  a looser title match with the same first author — report only
  same-title     identical title, different DOIs, neither a preprint (a correction? two editions?) — report only
`drop` is the tile to retire, `keep` the one that survives; same-title entries have no drop.
"""
import difflib
import re

from src.title_clean import norm

NOT_THE_PAPER = re.compile(r"^\s*(reply to|correction|erratum|corrigendum|retraction)\b", re.I)
SIMILAR = 0.85
# Tiles a person confirmed are the same work as a published tile, though the titles differ too much to match
# automatically: {retired tile's DOI: surviving tile's DOI}. Preprints, plus one conference abstract.
CONFIRMED_TWINS = {
    "10.1101/2021.04.08.439079": "10.1016/j.devcel.2023.05.017",
    "10.1101/2022.09.03.505525": "10.1038/s41586-023-06956-y",
    "10.1101/2024.06.16.599227": "10.1038/s44318-026-00807-y",
    "10.1016/j.fertnstert.2022.08.302": "10.1038/s41467-025-61441-6",
}
POSSIBLE = 0.65   # similar title + same first author: reported for a human, never retired automatically
BIORXIV_PREFIXES = ("10.1101/", "10.64898/")


def _live(papers):
    return [p for p in papers if not p.get("rejected")]


_ELIFE = re.compile(r"^(10\.7554/elife\.\d+)(\.\d+)?$")


def _elife_parts(doi: str):
    m = _ELIFE.match((doi or "").strip().lower())
    return (m.group(1), bool(m.group(2))) if m else ("", False)


def _first_surname(p) -> str:
    first = re.split(r",", p.get("authors") or "")[0]
    toks = re.sub(r"[^a-z\s]", "", first.lower()).split()
    return toks[-1] if toks else ""


def _year(p) -> int:
    m = re.match(r"\d{4}", str(p.get("year") or ""))
    return int(m.group()) if m else 0


def find_duplicates(papers: list[dict]) -> list[dict]:
    live = _live(papers)
    found, claimed = [], set()

    def add(kind, keep, drop):
        if drop is not None:
            if id(drop) in claimed:
                return
            claimed.add(id(drop))
        found.append({"kind": kind, "keep": keep, "drop": drop})

    # 1. versioned eLife DOIs of the same article
    by_base = {}
    for p in live:
        base, _ = _elife_parts(p.get("doi"))
        if base:
            by_base.setdefault(base, []).append(p)
    for group in by_base.values():
        if len(group) > 1:
            group.sort(key=lambda p: _elife_parts(p.get("doi"))[1])   # unversioned DOI first
            for drop in group[1:]:
                add("version-doi", group[0], drop)

    early = lambda p: p.get("preprint") or p.get("conference_abstract")   # versions that precede / stand in for the full paper
    by_doi = {(p.get("doi") or "").strip().lower(): p for p in live}
    for drop_doi, keep_doi in CONFIRMED_TWINS.items():
        drop, keep = by_doi.get(drop_doi.lower()), by_doi.get(keep_doi.lower())
        if drop is not None and keep is not None and drop is not keep:
            add("preprint-twin", keep, drop)
    pre = [p for p in live if early(p) and id(p) not in claimed]
    pub = [p for p in live if not early(p) and id(p) not in claimed]
    # 2. preprint tile vs published tile
    for a in pre:
        if NOT_THE_PAPER.match(a.get("title") or ""):
            continue
        best, best_r = None, 0.0
        for b in pub:
            if NOT_THE_PAPER.match(b.get("title") or "") or (b.get("year") and a.get("year") and _year(b) < _year(a)):
                continue
            r = 1.0 if norm(a["title"]) == norm(b["title"]) else difflib.SequenceMatcher(None, norm(a["title"]), norm(b["title"])).ratio()
            if r > best_r:
                best, best_r = b, r
        if best is not None and best_r >= SIMILAR:
            add("preprint-twin", best, a)
        elif best is not None and best_r >= POSSIBLE and _first_surname(a) and _first_surname(a) == _first_surname(best):
            found.append({"kind": "possible-twin", "keep": best, "drop": None, "others": [a]})

    # 3. the same preprint twice
    seen = {}
    for p in pre:
        if id(p) in claimed:
            continue
        k = norm(p.get("title") or "")
        if not k:
            continue
        if k in seen:
            first = seen[k]
            keep, drop = (first, p) if (first.get("doi") or "") else (p, first)   # keep the one that has a DOI
            add("preprint-pair", keep, drop)
        else:
            seen[k] = p

    # 4. identical title, different DOI, neither retired above: report for a human
    titles = {}
    for p in live:
        if id(p) in claimed or NOT_THE_PAPER.match(p.get("title") or ""):
            continue
        titles.setdefault(norm(p.get("title") or ""), []).append(p)
    for k, group in titles.items():
        if k and len(group) > 1:
            add("same-title", group[0], None)
            found[-1]["others"] = group[1:]
    return found


def retire(papers: list[dict], keep: dict, drop: dict, today: str) -> None:
    """Retire `drop` in favour of `keep`, moving over anything the survivor lacks."""
    old = (drop.get("doi") or "").strip()
    keep["previous_dois"] = sorted(set((keep.get("previous_dois") or []) + (drop.get("previous_dois") or []) + ([old] if old else [])) - {(keep.get("doi") or "").strip()})
    if not keep["previous_dois"]:
        keep.pop("previous_dois")
    # a conference abstract's PDF, summary and relevance note describe the abstract, not the full paper
    fields = ("ru_pick", "vip_author") if drop.get("conference_abstract") else ("ru_pick", "vip_author", "pdf_link", "summary", "relevance")
    for field in fields:
        if drop.get(field) and not keep.get(field):
            keep[field] = drop[field]
    drop["rejected"] = True
    drop["superseded_by"] = (keep.get("doi") or "").strip()
    drop["preprint_checked"] = today
