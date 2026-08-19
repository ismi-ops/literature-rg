"""Claude-powered relevance scoring and summary generation."""
import json
import re
import anthropic

from src.config import RELEVANCE_CONTEXT, KNOWN_TAGS

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def score_and_summarize(paper: dict) -> dict:
    """
    Score a paper's relevance to Ru's interests (0-10) and generate a contextual
    summary. Returns the paper dict enriched with score, summary, tags, and type.
    """
    title = paper.get("title", "")
    abstract = (paper.get("abstract", "") or "")[:2500]
    authors = paper.get("authors", [])
    venue = paper.get("journal", "")
    year = paper.get("year", "")
    pub_type = paper.get("pub_type", "research")

    author_str = ", ".join(str(a) for a in authors[:6])
    if len(authors) > 6:
        author_str += " et al."

    tags_list = ", ".join(KNOWN_TAGS)

    prompt = f"""You are helping curate a research paper reading list for Ru Gunawardane at the Allen Institute for Cell Science (AICS).

Background on Ru's interests:
{RELEVANCE_CONTEXT}

Paper to evaluate:
Title: {title}
Authors: {author_str}
Year: {year}
Journal/Venue: {venue}
Abstract: {abstract}

Respond with valid JSON only (no markdown fences):
{{
  "score": <integer 0-10>,
  "summary": "<3-5 sentences: what this paper does, why it matters scientifically, and specifically how it connects to AICS work or Ru's strategic interests. Write for a science-savvy executive. Empty string if insufficient info.>",
  "tags": "<comma-separated subset of: {tags_list}>",
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
        # Strip markdown fences if present
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
