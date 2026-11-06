"""
Attach a local PDF to a paper in papers.json.

Usage:
    python add_pdf.py paper.pdf --doi "10.1234/example"
    python add_pdf.py paper.pdf --title "word from title"
    python add_pdf.py paper.pdf --list          # show papers missing a PDF
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from src import storage


PDFS_DIR = Path(__file__).parent / "pdfs"


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80].strip("-")


def _find_paper(papers: list[dict], doi: str = "", title: str = "") -> dict | None:
    if doi:
        doi_lower = doi.strip().lower()
        for p in papers:
            if (p.get("doi") or "").strip().lower() == doi_lower:
                return p
        print(f"No paper found with DOI: {doi}")
        return None

    if title:
        query = title.strip().lower()
        matches = [p for p in papers if query in (p.get("title") or "").lower()]
        if not matches:
            print(f"No paper found matching: {title!r}")
            return None
        if len(matches) > 1:
            print(f"Multiple matches for {title!r}:")
            for i, p in enumerate(matches):
                print(f"  [{i}] {p['title'][:80]}")
            idx = input("Enter index to select: ").strip()
            return matches[int(idx)]
        return matches[0]

    return None


def list_missing(papers: list[dict]) -> None:
    missing = [p for p in papers if not p.get("pdf_link")]
    if not missing:
        print("All papers have PDF links.")
        return
    print(f"{len(missing)} paper(s) without a PDF link:\n")
    for p in missing:
        doi = p.get("doi") or "(no DOI)"
        print(f"  DOI: {doi}")
        print(f"  Title: {p.get('title', '')[:80]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Attach a PDF to a paper")
    parser.add_argument("pdf", nargs="?", help="Path to the PDF file")
    parser.add_argument("--doi", help="DOI of the paper to attach to")
    parser.add_argument("--title", help="Title substring to identify the paper")
    parser.add_argument("--list", action="store_true", help="List papers missing a PDF")
    parser.add_argument("--no-regen", action="store_true",
                        help="Skip regenerating index.html")
    args = parser.parse_args()

    papers = storage.load_papers()

    if args.list:
        list_missing(papers)
        return

    if not args.pdf:
        parser.error("PDF file is required (or use --list)")

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        sys.exit(f"Expected a .pdf file, got: {pdf_path.suffix}")

    if not args.doi and not args.title:
        parser.error("Provide --doi or --title to identify the paper")

    paper = _find_paper(papers, doi=args.doi or "", title=args.title or "")
    if not paper:
        sys.exit(1)

    print(f"Matched: {paper['title'][:80]}")

    # Build destination filename: prefer DOI slug, fall back to title slug
    if paper.get("doi"):
        slug = _slugify(paper["doi"])
    else:
        slug = _slugify(paper.get("title", "paper"))
    dest = PDFS_DIR / f"{slug}.pdf"

    if dest.exists():
        overwrite = input(f"{dest.name} already exists. Overwrite? [y/N] ").strip().lower()
        if overwrite != "y":
            sys.exit("Aborted.")

    PDFS_DIR.mkdir(exist_ok=True)
    shutil.copy2(pdf_path, dest)
    print(f"Copied → pdfs/{dest.name}")

    # Update the paper entry
    paper["pdf_link"] = f"pdfs/{dest.name}"
    storage.save_papers(papers)
    print("Updated papers.json")

    if not args.no_regen:
        result = subprocess.run(["python", "generate_site.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Regenerated index.html, filters.json, papers_data.json")
        else:
            print("Warning: generate_site.py failed:", result.stderr[:200])

    print(f"\nDone. Commit and push to publish:\n  git add pdfs/{dest.name} papers.json index.html filters.json papers_data.json && git commit -m 'feat: add PDF for {paper['title'][:50]}' && git push")


if __name__ == "__main__":
    main()
