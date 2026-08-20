"""
Research Paper Agent for Ru Gunawardane
----------------------------------------
Searches Semantic Scholar, bioRxiv, and PubMed for new biology papers,
scores them for relevance to Ru's interests using Claude, and adds
qualifying papers to papers.json (the GitHub Pages source of truth).

Usage:
    python agent.py                          # default: last 14 days, score ≥7
    python agent.py --days 30 --min-score 6
    python agent.py --dry-run                # score and print; don't write
"""
import os
import argparse
from datetime import date

from dotenv import load_dotenv

from src.config import SEARCH_QUERIES, PUBMED_QUERIES, TRACKED_AUTHORS
from src.sources.semantic_scholar import search_papers as ss_search, get_author_papers
from src.sources.biorxiv import fetch_recent as biorxiv_fetch
from src.sources.pubmed import search_pubmed
from src.sources.ss_recommendations import fetch_recommendations
from src.relevance import score_and_summarize
from src.sources.pdf_finder import get_pdf_link
from src import storage


# ── Deduplication ──────────────────────────────────────────────────────────────

def deduplicate(candidates: list[dict], existing: set[str]) -> list[dict]:
    seen_in_batch: set[str] = set()
    unique = []
    for paper in candidates:
        doi = (paper.get("doi") or "").strip().lower()
        title = (paper.get("title") or "").strip().lower()

        if doi and doi in existing:
            continue
        if title and title in existing:
            continue

        key = doi or title
        if not key or key in seen_in_batch:
            continue

        seen_in_batch.add(key)
        unique.append(paper)

    return unique


# ── Main ───────────────────────────────────────────────────────────────────────

def run_agent(days_back: int = 14, min_score: int = 7, dry_run: bool = False):
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Note: ANTHROPIC_API_KEY not set — using keyword-based relevance scoring")

    print("Fetching existing papers from papers.json...")
    existing = storage.get_existing_papers()
    papers_json = storage.load_papers()
    print(f"  {len(papers_json)} existing entries found")

    candidates: list[dict] = []

    # ── Semantic Scholar: topic queries ───────────────────────────────────────
    print(f"\nSearching Semantic Scholar by topic (last {days_back} days)...")
    for query in SEARCH_QUERIES:
        results = ss_search(query, days_back=days_back, limit=8)
        if results:
            print(f"  [{len(results)}]  {query}")
        candidates.extend(results)

    # ── Semantic Scholar: tracked authors ─────────────────────────────────────
    print(f"\nChecking tracked authors on Semantic Scholar...")
    for author in TRACKED_AUTHORS:
        results = get_author_papers(author, days_back=days_back)
        if results:
            print(f"  [{len(results)}]  {author}")
        candidates.extend(results)

    # ── bioRxiv: category-based sweep ─────────────────────────────────────────
    print(f"\nFetching bioRxiv preprints (last {days_back} days)...")
    biorxiv_papers = biorxiv_fetch(days_back=days_back)
    print(f"  {len(biorxiv_papers)} preprints in relevant categories")
    candidates.extend(biorxiv_papers)

    # ── PubMed: complementary journal coverage ────────────────────────────────
    print(f"\nSearching PubMed (last {days_back} days)...")
    for query in PUBMED_QUERIES:
        results = search_pubmed(query, days_back=days_back, max_results=8)
        if results:
            print(f"  [{len(results)}]  {query}")
        candidates.extend(results)

    # ── Semantic Scholar: recommendations seeded from reading list ────────────
    print(f"\nFetching Semantic Scholar recommendations...")
    rec_papers = fetch_recommendations(papers_json)
    print(f"  {len(rec_papers)} recommendations returned")
    candidates.extend(rec_papers)

    print(f"\n{len(candidates)} total candidates before deduplication")
    unique = deduplicate(candidates, existing)
    print(f"{len(unique)} unique new candidates\n")

    if not unique:
        print("No new candidates to evaluate. Done.")
        return

    # ── Relevance scoring ─────────────────────────────────────────────────────
    print(f"Scoring relevance (threshold: {min_score}/10)...")
    scored = []
    today = date.today().isoformat()
    for i, paper in enumerate(unique):
        title_short = (paper.get("title") or "")[:65]
        print(f"  [{i+1:3d}/{len(unique)}] {title_short}...")
        result = score_and_summarize(paper)
        result["added"] = today
        result["pdf_link"] = get_pdf_link(paper) or ""
        score = result.get("score", 0)
        reasoning = result.get("reasoning", "")
        if score >= min_score:
            print(f"           → {score}/10  ✓  {reasoning}")
        scored.append(result)

    # ── Filter and rank ───────────────────────────────────────────────────────
    selected = sorted(
        [p for p in scored if p.get("score", 0) >= min_score],
        key=lambda x: x["score"],
        reverse=True,
    )

    print(f"\n{len(selected)} papers meet the relevance threshold (≥{min_score}/10)")

    if not selected:
        print("Nothing to add. Done.")
        return

    if dry_run:
        print("\n[DRY RUN] Would add the following to papers.json:")
        for p in selected:
            print(f"  [{p['score']}/10] {p.get('title', '')[:80]}")
            print(f"          {p.get('journal', '')} | {p.get('year', '')}")
        return

    # ── Write to papers.json ──────────────────────────────────────────────────
    print(f"\nAdding to papers.json...")
    added = storage.add_papers(selected)
    print(f"\nDone. Added {added}/{len(selected)} papers to papers.json.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Literature agent — finds and adds relevant papers for Ru Gunawardane"
    )
    parser.add_argument(
        "--days", type=int, default=14,
        help="How many days back to search (default: 14)"
    )
    parser.add_argument(
        "--min-score", type=int, default=7,
        help="Minimum relevance score 0-10 (default: 7)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Score papers but don't write to papers.json"
    )
    args = parser.parse_args()

    run_agent(days_back=args.days, min_score=args.min_score, dry_run=args.dry_run)
