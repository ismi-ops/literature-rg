"""Backfill pdf_link for existing papers in papers.json that don't have one."""
from src import storage
from src.sources.pdf_finder import get_pdf_link


def main():
    papers = storage.load_papers()
    updated = 0
    for paper in papers:
        if paper.get("pdf_link"):
            continue
        title = (paper.get("title") or "")[:60]
        pdf = get_pdf_link(paper)
        if pdf:
            paper["pdf_link"] = pdf
            updated += 1
            print(f"  ✓ {title}...")
            print(f"      {pdf}")
        else:
            print(f"  – {title}...")
    if updated:
        storage.save_papers(papers)
        print(f"\nUpdated {updated} papers with PDF links.")
    else:
        print("\nNo new PDF links found.")


if __name__ == "__main__":
    main()
