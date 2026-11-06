"""
Match PDFs in the pdfs/ directory to papers in papers.json and update pdf_link.

Naming convention: the PDF filename should be the DOI slug
  e.g. 10.1038/s41580-023-00688-7  →  10-1038-s41580-023-00688-7.pdf
       (non-alphanumeric chars replaced with hyphens)

Falls back to matching by title slug for papers without a DOI.
Run by the sync_pdfs GitHub Actions workflow when pdfs/ changes.
"""
import re
import subprocess
import sys
from pathlib import Path

from src import storage

PDFS_DIR = Path(__file__).parent / "pdfs"


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")[:80]


def main():
    papers = storage.load_papers()

    # Build lookup: slug → paper index
    slug_to_idx: dict[str, int] = {}
    for i, p in enumerate(papers):
        if p.get("doi"):
            slug_to_idx[_slugify(p["doi"])] = i
        title = (p.get("title") or "").strip()
        if title:
            slug_to_idx[_slugify(title)[:60].strip("-")] = i

    pdf_files = [f for f in PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf" and f.name != ".gitkeep"]
    if not pdf_files:
        print("No PDFs found in pdfs/.")
        return

    updated = 0
    unmatched = []
    for pdf in pdf_files:
        stem = _slugify(pdf.stem)
        idx = slug_to_idx.get(stem)
        if idx is None:
            # Prefix match (truncated title slugs) — only when it identifies exactly one paper
            hits = {i for slug, i in slug_to_idx.items() if stem.startswith(slug[:40]) or slug.startswith(stem[:40])}
            if len(hits) == 1:
                idx = hits.pop()

        if idx is None:
            unmatched.append(pdf.name)
            continue

        link = f"pdfs/{pdf.name}"
        if papers[idx].get("pdf_link") == link:
            continue  # already set

        papers[idx]["pdf_link"] = link
        print(f"  Matched {pdf.name} → {papers[idx]['title'][:70]}")
        updated += 1

    if updated:
        storage.save_papers(papers)
        result = subprocess.run(["python", "generate_site.py"], capture_output=True, text=True)
        if result.returncode != 0:
            print("generate_site.py error:", result.stderr[:300], file=sys.stderr)
            sys.exit(1)
        print(f"\nUpdated {updated} paper(s) and regenerated index.html.")
    else:
        print("No new matches found.")

    if unmatched:
        print(f"\nCould not match {len(unmatched)} PDF(s) to any paper:")
        for name in unmatched:
            print(f"  {name}")
        print("Check the filename matches the paper's DOI slug.")


if __name__ == "__main__":
    main()
