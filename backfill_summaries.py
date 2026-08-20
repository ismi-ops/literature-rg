"""Backfill summaries for papers in papers.json that don't have one."""
from src import storage
from src.relevance import score_and_summarize


def main():
    papers = storage.load_papers()
    updated = 0
    for paper in papers:
        if paper.get("summary"):
            continue
        title = (paper.get("title") or "")[:60]
        print(f"  Summarising: {title}...")
        result = score_and_summarize(paper)
        summary = result.get("summary", "")
        if summary:
            paper["summary"] = summary
            updated += 1
            print(f"    ✓ done")
        else:
            print(f"    – no summary returned")
    if updated:
        storage.save_papers(papers)
        print(f"\nUpdated {updated} papers with summaries.")
    else:
        print("\nAll papers already have summaries.")


if __name__ == "__main__":
    main()
