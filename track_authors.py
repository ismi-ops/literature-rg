"""
Fetch recent papers from VIP authors and add to papers.json.

Usage:
    python track_authors.py                     # lookback 14 days
    python track_authors.py --lookback-days 30
    python track_authors.py --vip-threshold 6   # min score for main feed (default 6)
    python track_authors.py --dry-run

Age rules:
  - Papers older than 10 years are excluded entirely.
  - Papers 5–10 years old require score >= vip_threshold + 2 (landmark/super-relevant only).
  - Papers < 5 years old use the standard vip_threshold.
"""
import argparse
from datetime import date, timedelta

from dotenv import load_dotenv

from src import storage
from src.relevance import score_and_summarize
from src.sources.author_tracker import fetch_all_recent
from src.sources.pdf_finder import get_pdf_link

MAX_AGE_YEARS = 10
OLD_PAPER_EXTRA = 2   # extra score points needed for papers 5–10 years old


def _age_threshold(paper_year: str, today_year: int, base_threshold: int) -> int | None:
    """
    Return the score threshold for this paper, or None to skip entirely.
    None  → exclude (older than MAX_AGE_YEARS)
    int   → minimum score required
    """
    try:
        year = int(paper_year)
    except (TypeError, ValueError):
        return base_threshold  # unknown year: apply base threshold

    age = today_year - year
    if age > MAX_AGE_YEARS:
        return None
    if age >= 5:
        return base_threshold + OLD_PAPER_EXTRA
    return base_threshold


def run(lookback_days: int = 14, vip_threshold: int = 6, dry_run: bool = False):
    load_dotenv()
    since_date = (date.today() - timedelta(days=lookback_days)).isoformat()
    today_year = date.today().year
    print(f"Fetching papers published since {since_date} from VIP authors...")
    print(f"Age rules: exclude >10 yrs; require score ≥{vip_threshold + OLD_PAPER_EXTRA} for 5–10 yr old papers.")

    papers = fetch_all_recent(since_date)
    print(f"\nFound {len(papers)} candidate paper(s) across all VIP authors.")

    if not papers:
        print("Nothing to do.")
        return

    existing = storage.get_existing_papers()
    added_count = 0
    skipped_count = 0
    excluded_count = 0

    for paper in papers:
        doi_key = (paper.get("doi") or "").strip().lower()
        title_key = (paper.get("title") or "").strip().lower()
        if (doi_key and doi_key in existing) or (title_key and title_key in existing):
            skipped_count += 1
            continue

        effective_threshold = _age_threshold(paper.get("year", ""), today_year, vip_threshold)
        if effective_threshold is None:
            excluded_count += 1
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
        age = today_year - int(paper.get("year") or today_year)
        age_note = f", age {age} yr → threshold {effective_threshold}" if age >= 5 else ""
        print(f"    Score: {score}/10  [{paper['vip_author']}]{age_note}")

        if score < effective_threshold:
            print(f"    → skipped (score {score} < {effective_threshold})")
            excluded_count += 1
            continue

        if score < vip_threshold:
            result["vip_only"] = True
            print(f"    → vip_only (score {score} < main-feed threshold {vip_threshold})")
        else:
            print(f"    → main feed")

        if dry_run:
            continue

        storage.add_papers([result])
        added_count += 1

    if dry_run:
        eligible = len(papers) - skipped_count - excluded_count
        print(f"\n[DRY RUN] Would have added ~{eligible} paper(s) "
              f"({skipped_count} already present, {excluded_count} excluded by age/score).")
        return

    print(f"\nAdded {added_count} new paper(s). "
          f"Skipped {skipped_count} already present, {excluded_count} excluded by age/score.")
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
