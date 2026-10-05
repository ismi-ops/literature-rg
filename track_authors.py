"""
Fetch recent papers from VIP authors and add to papers.json.

Usage:
    python track_authors.py                    # lookback 14 days
    python track_authors.py --lookback-days 30
    python track_authors.py --vip-threshold 6  # min score for main feed (default 6)
    python track_authors.py --dry-run
"""
import argparse
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from src import storage
from src.relevance import score_and_summarize
from src.sources.author_tracker import fetch_all_recent
from src.sources.pdf_finder import get_pdf_link


def run(lookback_days: int = 14, vip_threshold: int = 6, dry_run: bool = False):
    load_dotenv()
    since_date = (date.today() - timedelta(days=lookback_days)).isoformat()
    print(f"Fetching papers published since {since_date} from VIP authors...")

    papers = fetch_all_recent(since_date)
    print(f"\nFound {len(papers)} candidate paper(s) across all VIP authors.")

    if not papers:
        print("Nothing to do.")
        return

    existing = storage.get_existing_papers()
    added_count = 0
    skipped_count = 0

    for paper in papers:
        doi_key = (paper.get("doi") or "").strip().lower()
        title_key = (paper.get("title") or "").strip().lower()
        if (doi_key and doi_key in existing) or (title_key and title_key in existing):
            skipped_count += 1
            continue

        print(f"\n  [{paper['vip_author']}] {paper['title'][:80]}")
        result = score_and_summarize(paper)
        result["added"] = date.today().isoformat()
        result["curated"] = False
        result["source"] = "author_tracker"
        result["vip_author"] = paper["vip_author"]
        result["preprint"] = paper.get("preprint", False)

        if not result.get("pdf_link"):
            result["pdf_link"] = get_pdf_link(paper) or ""

        score = result.get("score", 0)
        print(f"    Score: {score}/10  [{paper['vip_author']}]")

        if score < vip_threshold:
            result["vip_only"] = True
            print(f"    → vip_only (score {score} < threshold {vip_threshold})")
        else:
            print(f"    → main feed")

        if dry_run:
            continue

        storage.add_papers([result])
        added_count += 1

    if dry_run:
        print(f"\n[DRY RUN] Would have added {len(papers) - skipped_count} paper(s) ({skipped_count} already present).")
        return

    print(f"\nAdded {added_count} new paper(s). Skipped {skipped_count} already in papers.json.")
    if added_count:
        print("Run `python generate_site.py` to regenerate index.html.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch recent papers from VIP authors")
    parser.add_argument("--lookback-days", type=int, default=14,
                        help="How many days back to look for new papers (default: 14)")
    parser.add_argument("--vip-threshold", type=int, default=6,
                        help="Min score for main feed; below this gets vip_only (default: 6)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score and report but don't write to papers.json")
    args = parser.parse_args()
    run(lookback_days=args.lookback_days, vip_threshold=args.vip_threshold, dry_run=args.dry_run)
