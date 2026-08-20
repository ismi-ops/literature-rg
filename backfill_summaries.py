"""Backfill summaries and relevance notes for papers that are missing them."""
from src import storage
from src.relevance import score_and_summarize


def main():
    papers = storage.load_papers()
    updated = 0
    for paper in papers:
        needs_summary = not paper.get("summary")
        needs_relevance = not paper.get("relevance")
        if not needs_summary and not needs_relevance:
            continue
        title = (paper.get("title") or "")[:60]
        print(f"  Processing: {title}...")
        result = score_and_summarize(paper)
        changed = False
        if needs_summary:
            summary = result.get("summary", "")
            if summary:
                paper["summary"] = summary
                changed = True
        if needs_relevance:
            relevance = result.get("relevance", "")
            if relevance:
                paper["relevance"] = relevance
                changed = True
        if changed:
            updated += 1
            print(f"    ✓ done")
        else:
            print(f"    – nothing returned")
    if updated:
        storage.save_papers(papers)
        print(f"\nUpdated {updated} papers.")
    else:
        print("\nAll papers already have summaries and relevance notes.")


if __name__ == "__main__":
    main()
