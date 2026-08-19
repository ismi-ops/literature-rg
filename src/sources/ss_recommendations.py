"""Semantic Scholar Recommendations API — seeded from papers already in the reading list."""
import time
import requests
from src.sources.semantic_scholar import FIELDS, _normalize

BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECS_URL = "https://api.semanticscholar.org/recommendations/v1/papers/"
MAX_SEEDS = 25   # SS recommends keeping seed lists under 100; 25 is plenty
MAX_RESULTS = 20


def _doi_to_ss_id(doi: str) -> str | None:
    """Resolve a DOI to a Semantic Scholar paper ID."""
    try:
        resp = requests.get(
            f"{BASE_URL}/paper/DOI:{doi}",
            params={"fields": "paperId"},
            timeout=15,
        )
        time.sleep(0.5)
        if resp.status_code == 200:
            return resp.json().get("paperId")
    except Exception:
        pass
    return None


def fetch_recommendations(papers_json: list[dict]) -> list[dict]:
    """
    Fetch paper recommendations seeded from the existing reading list.
    Uses the most recent papers that have DOIs as positive examples.
    """
    # Pick the most recent papers that have DOIs as seeds
    candidates = [p for p in papers_json if p.get("doi")]
    candidates.sort(key=lambda p: p.get("added", ""), reverse=True)
    seeds_meta = candidates[:MAX_SEEDS]

    if not seeds_meta:
        print("  No DOIs available for seeding recommendations.")
        return []

    print(f"  Resolving {len(seeds_meta)} seed paper IDs...")
    seed_ids = []
    for p in seeds_meta:
        ss_id = _doi_to_ss_id(p["doi"])
        if ss_id:
            seed_ids.append(ss_id)

    if not seed_ids:
        print("  Could not resolve any paper IDs for recommendations.")
        return []

    print(f"  Fetching recommendations from {len(seed_ids)} seeds...")
    try:
        resp = requests.post(
            RECS_URL,
            json={"positivePaperIds": seed_ids},
            params={"fields": FIELDS, "limit": MAX_RESULTS},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json().get("recommendedPapers", [])
        time.sleep(1.0)
    except Exception as e:
        print(f"  Recommendations API error: {e}")
        return []

    results = [_normalize(p) for p in raw if p.get("abstract")]
    results_with_source = [{**r, "source": "ss_recommendations"} for r in results]
    return results_with_source
