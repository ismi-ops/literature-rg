"""Tidy and backfill the summary and Cell Science relevance blurbs on every tile.

  1. Every existing summary is cleaned (a leading "BACKGROUND" / "SUMMARY" / "ABSTRACT" heading and stray
     line breaks are removed).
  2. A tile missing a summary or relevance blurb gets its abstract fetched by DOI (OpenAlex, then Semantic
     Scholar) and the blurbs are generated from it. Tiles with no abstract available are left alone, and a
     relevance blurb is only written when a Cell Science topic actually matches.
"""
import sys
import time

from src import storage
from src.relevance import score_and_summarize
from src.sources.abstracts import fetch_abstract
from src.summary_text import clean_summary


def main(fetch=fetch_abstract, pause: float = 0.3):
    papers = storage.load_papers()
    cleaned = filled_summary = filled_relevance = no_abstract = 0

    for paper in papers:
        if paper.get("summary"):
            tidy = clean_summary(paper["summary"])
            if tidy != paper["summary"]:
                paper["summary"] = tidy
                cleaned += 1

    for paper in papers:
        if paper.get("rejected"):
            continue
        needs_summary = not paper.get("summary")
        needs_relevance = not paper.get("relevance")
        if not (needs_summary or needs_relevance) or not paper.get("doi"):
            continue
        title = (paper.get("title") or "")[:60]
        abstract = paper.get("abstract") or fetch(paper["doi"])
        time.sleep(pause)
        if not abstract:
            no_abstract += 1
            print(f"  no abstract found: {title}")
            continue
        result = score_and_summarize(dict(paper, abstract=abstract))
        if needs_summary and result.get("summary"):
            paper["summary"] = result["summary"]
            filled_summary += 1
        if needs_relevance and result.get("relevance"):
            paper["relevance"] = result["relevance"]
            filled_relevance += 1
        print(f"  ✓ {title}")

    print(f"\nCleaned {cleaned} summaries; filled {filled_summary} summaries and {filled_relevance} relevance blurbs; "
          f"{no_abstract} tiles had no abstract available.")
    if cleaned or filled_summary or filled_relevance:
        storage.save_papers(papers)


if __name__ == "__main__":
    sys.exit(main())
