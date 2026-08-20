"""Relevance scoring and summary generation.

Uses Claude when ANTHROPIC_API_KEY is set; falls back to keyword scoring otherwise.
"""
import json
import os
import re

from src.config import RELEVANCE_CONTEXT, KNOWN_TAGS

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


# ── Keyword fallback ───────────────────────────────────────────────────────────

# Each entry: (keywords, points)  — matched against lowercase title+abstract
_KEYWORD_RULES = [
    # Core topics — high value
    (["morphogenesis", "tissue morphogenesis"], 3),
    (["synthetic biology", "synthetic developmental"], 3),
    (["cell fate", "fate decision", "fate transition"], 3),
    (["mechanobiology", "tissue mechanics", "mechanical force"], 3),
    (["self-organization", "self-organiz"], 3),
    (["gene circuit", "genetic circuit", "synthetic circuit"], 3),
    (["foundation model", "virtual cell", "AI cell biology"], 3),
    # Secondary topics — moderate value
    (["organoid", "lumenogenesis", "lumen formation"], 2),
    (["stem cell", "iPSC", "pluripotent"], 2),
    (["bioelectricity", "bioelectric", "membrane voltage"], 2),
    (["spatial transcriptomics", "spatial biology", "spatial cell"], 2),
    (["tissue fluidity", "solid-fluid", "fluid-solid"], 2),
    (["Turing pattern", "reaction-diffusion", "reaction diffusion"], 2),
    (["phase separation", "condensate", "biomolecular condensate"], 2),
    (["collective migration", "collective cell"], 2),
    (["multicellular", "multi-cellular"], 2),
    (["live-cell imaging", "live cell imaging", "live imaging", "morphodynamics"], 2),
    (["image-based profiling", "cell painting", "phenomics", "high-content imaging"], 2),
    (["phenotype-genotype", "phenotype genotype", "morpho-dynamic", "morphodynamic phenotype"], 3),
    (["single-cell", "single cell omics", "scRNA"], 1),
    (["patterning", "tissue patterning", "developmental patterning"], 1),
    (["development", "developmental biology"], 1),
    (["cell state", "cell identity"], 1),
    (["machine learning", "deep learning", "neural network"], 1),
]

# Tracked author names — finding any of these adds points
_TRACKED_AUTHORS = [
    "Morsut", "Elowitz", "Zernicka-Goetz", "Liberali", "Levin",
    "Wickstrom", "Hannezo", "Ebisuya", "Petridou", "Streichan",
    "Priya", "Toettcher", "Bintu", "Garcia-Ojalvo",
]

# High-impact journals add a point
_TOP_JOURNALS = [
    "Nature Cell Biology", "Nature Reviews Molecular Cell Biology",
    "Cell Systems", "Cell", "Nature Biotechnology", "Nature Communications",
    "Development", "Developmental Cell", "eLife", "Science", "Nature",
]


def _keyword_score(paper: dict) -> dict:
    """Simple keyword + author heuristic used when no Anthropic key is available."""
    text = ((paper.get("title") or "") + " " + (paper.get("abstract") or "")).lower()
    authors = " ".join(str(a) for a in (paper.get("authors") or []))
    journal = paper.get("journal", "") or ""

    points = 0
    matched_tags = []

    for keywords, pts in _KEYWORD_RULES:
        if any(kw.lower() in text for kw in keywords):
            points += pts
            # Map first keyword to a tag where possible
            matched_tags.append(keywords[0])

    for author in _TRACKED_AUTHORS:
        if author.lower() in authors.lower():
            points += 2
            break

    if any(j.lower() in journal.lower() for j in _TOP_JOURNALS):
        points += 1

    # Normalise to 0-10 (raw points cap at ~15 for a perfect paper)
    score = min(10, round(points * 10 / 12))

    tags = ", ".join(
        t for t in KNOWN_TAGS
        if any(t.lower() in text for t in [t])
    )

    pub_type = paper.get("pub_type", "research")

    author_list = paper.get("authors", [])
    author_str = ", ".join(str(a) for a in author_list[:6])
    if len(author_list) > 6:
        author_str += " et al."

    paper_out = dict(paper)
    paper_out.update({
        "authors": author_str,
        "year": str(paper.get("year", "")) if paper.get("year") else "",
        "score": score,
        "summary": "",  # No summary without Claude
        "tags": tags,
        "type": pub_type,
        "reasoning": "keyword match (no Anthropic API key)",
    })
    return paper_out


# ── Main public function ───────────────────────────────────────────────────────

def score_and_summarize(paper: dict) -> dict:
    """
    Score a paper's relevance to Ru's interests (0-10) and generate a summary.
    Uses Claude when ANTHROPIC_API_KEY is available; keyword scoring otherwise.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _keyword_score(paper)

    title = paper.get("title", "")
    abstract = (paper.get("abstract", "") or "")[:2500]
    authors = paper.get("authors", [])
    venue = paper.get("journal", "")
    year = paper.get("year", "")
    pub_type = paper.get("pub_type", "research")

    author_str = ", ".join(str(a) for a in authors[:6])
    if len(authors) > 6:
        author_str += " et al."

    publisher_keywords = paper.get("publisher_keywords") or []
    pub_kw_str = ", ".join(publisher_keywords[:10]) if publisher_keywords else "none"
    tags_list = ", ".join(KNOWN_TAGS)

    prompt = f"""You are helping curate a research paper reading list for Ru Gunawardane at the Allen Institute for Cell Science (AICS).

Background on Ru's interests:
{RELEVANCE_CONTEXT}

Paper to evaluate:
Title: {title}
Authors: {author_str}
Year: {year}
Journal/Venue: {venue}
Publisher-assigned keywords/categories: {pub_kw_str}
Abstract: {abstract}

Respond with valid JSON only (no markdown fences):
{{
  "score": <integer 0-10>,
  "summary": "<3-5 sentences: what this paper does, why it matters scientifically, and specifically how it connects to AICS work or Ru's strategic interests. Write for a science-savvy executive. Empty string if insufficient info.>",
  "tags": "<comma-separated subset of: {tags_list} — topic tags only, NEVER use author names, lab names, or paper types (research/review/perspective)>",
  "type": "<research | review | perspective>",
  "reasoning": "<1 sentence explaining the score>"
}}

Scoring guide:
- 9-10: Directly on Ru's core topics, from a high-impact journal, clear AICS relevance
- 7-8: Relevant to ≥2 of Ru's interest areas, or from a tracked author/lab
- 5-6: Tangentially relevant, interesting but lower priority
- 0-4: Not relevant to Ru's interests"""

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        result = json.loads(json_match.group()) if json_match else {"score": 0}
    except Exception as e:
        print(f"    Claude API error: {e}")
        result = {"score": 0}

    paper_out = dict(paper)
    paper_out.update({
        "authors": author_str,
        "year": str(year) if year else "",
        "score": int(result.get("score", 0)),
        "summary": result.get("summary", ""),
        "tags": result.get("tags", ""),
        "type": result.get("type", pub_type),
        "reasoning": result.get("reasoning", ""),
    })
    return paper_out
