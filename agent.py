"""
Research Paper Agent for Ru Gunawardane
----------------------------------------
Searches Semantic Scholar, bioRxiv, and PubMed for new biology papers,
scores them for relevance to Ru's interests using Claude, and adds
qualifying papers to the Smartsheet repository.

Usage:
    python agent.py                          # default: last 14 days, score ≥7
    python agent.py --days 30 --min-score 6
    python agent.py --dry-run                # score and print; don't write
"""
import os
import argparse

from dotenv import load_dotenv

from src.config import SEARCH_QUERIES, PUBMED_QUERIES, TRACKED_AUTHORS
from src.sources.semantic_scholar import search_papers as ss_search, get_author_papers
from src.sources.biorxiv import fetch_recent as biorxiv_fetch
from src.sources.pubmed import search_pubmed
from src.relevance import score_and_summarize
from src.smartsheet_client import SmartsheetClient


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

    smartsheet_key = os.environ.get("SMARTSHEET_API_KEY")
    if not smartsheet_key:
        raise ValueError("SMARTSHEET_API_KEY environment variable not set")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    ss_client = SmartsheetClient(api_key=smartsheet_key)

    print(f"Fetching existing papers from Smartsheet...")
    existing = ss_client.get_existing_papers()
    print(f"  {len(existing)} existing entries found")

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

    print(f"\n{len(candidates)} total candidates before deduplication")
    unique = deduplicate(candidates, existing)
    print(f"{len(unique)} unique new candidates\n")

    if not unique:
        print("No new candidates to evaluate. Done.")
        return

    # ── Relevance scoring ─────────────────────────────────────────────────────
    print(f"Scoring relevance with Claude (threshold: {min_score}/10)...")
    scored = []
    for i, paper in enumerate(unique):
        title_short = (paper.get("title") or "")[:65]
        print(f"  [{i+1:3d}/{len(unique)}] {title_short}...")
        result = score_and_summarize(paper)
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
        print("\n[DRY RUN] Would add the following to Smartsheet:")
        for p in selected:
            print(f"  [{p['score']}/10] {p.get('title', '')[:80]}")
            print(f"          {p.get('journal', '')} | {p.get('year', '')}")
        return

    # ── Write to Smartsheet ───────────────────────────────────────────────────
    print(f"\nAdding to Smartsheet...")
    added = 0
    for paper in selected:
        title_short = (paper.get("title") or "")[:70]
        if ss_client.add_paper(paper):
            added += 1
            print(f"  ✓ [{paper['score']}/10] {title_short}")
        else:
            print(f"  ✗ Failed: {title_short}")

    print(f"\nDone. Added {added}/{len(selected)} papers to Smartsheet.")


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
        help="Minimum Claude relevance score 0-10 (default: 7)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Score papers but don't write to Smartsheet"
    )
    args = parser.parse_args()

    run_agent(days_back=args.days, min_score=args.min_score, dry_run=args.dry_run)
