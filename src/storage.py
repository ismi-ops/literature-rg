"""JSON-based paper storage (replaces Smartsheet client)."""
import json
import os
from pathlib import Path

_PAPERS_PATH = Path(__file__).parent.parent / "papers.json"


def get_existing_papers() -> set[str]:
    """Return set of lowercase DOIs and titles already in papers.json."""
    if not _PAPERS_PATH.exists():
        return set()
    with open(_PAPERS_PATH) as f:
        papers = json.load(f)
    existing = set()
    for p in papers:
        doi = (p.get("doi") or "").strip().lower()
        title = (p.get("title") or "").strip().lower()
        if doi:
            existing.add(doi)
        if title:
            existing.add(title)
    return existing


def load_papers() -> list[dict]:
    if not _PAPERS_PATH.exists():
        return []
    with open(_PAPERS_PATH) as f:
        return json.load(f)


def save_papers(papers: list[dict]) -> None:
    with open(_PAPERS_PATH, "w") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
        f.write("\n")


def add_papers(new_papers: list[dict]) -> int:
    """Append new papers to papers.json. Returns count added."""
    existing = load_papers()
    existing_keys = get_existing_papers()
    added = 0
    for paper in new_papers:
        doi = (paper.get("doi") or "").strip().lower()
        title = (paper.get("title") or "").strip().lower()
        key = doi or title
        if key and key in existing_keys:
            continue
        # Normalize tags to list
        tags = paper.get("tags", "")
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        paper_entry = {
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "year": str(paper.get("year", "")) if paper.get("year") else "",
            "journal": paper.get("journal", ""),
            "type": paper.get("type", "research"),
            "summary": paper.get("summary", ""),
            "relevance": paper.get("relevance", ""),
            "tags": tags,
            "doi": paper.get("doi", ""),
            "link": paper.get("link", "") or paper.get("url", ""),
            "score": paper.get("score", 0),
            "added": paper.get("added", ""),
        }
        existing.append(paper_entry)
        existing_keys.add(key)
        added += 1
    if added:
        save_papers(existing)
    return added
