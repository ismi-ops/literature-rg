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
    # Core Cell Science topics — highest value
    (["endogenous tag", "mEGFP", "knock-in fluorescent", "CRISPR tag hiPSC"], 3),
    (["intracellular organization", "organelle positioning", "organelle variation"], 3),
    (["holistic cell state", "cell state imaging morphology"], 3),
    (["cell decision", "cell fate decision", "bistability", "stochastic switching", "signal integration threshold"], 3),
    (["lumen morphogenesis", "lumenoid", "lumen pressure", "lumen mechanics", "hydraulic lumen"], 3),
    (["novel method", "new method", "experimental design", "imaging platform", "microscopy method", "biosensor"], 2),
    (["hiPSC cardiomyocyte", "iPSC-CM", "cardiomyocyte maturation", "sarcomere"], 1),
    (["synthoid", "synthetic cell community", "CellScapes"], 3),
    (["morpho-dynamic", "morphodynamic phenotype", "phenotype-genotype coupling"], 3),
    (["virtual cell", "generative cell model", "VAE cell morphology"], 3),
    # Core biology topics — high value
    (["morphogenesis", "tissue morphogenesis"], 3),
    (["synthetic biology", "synthetic developmental"], 3),
    (["cell fate", "fate decision", "fate transition"], 3),
    (["mechanobiology", "tissue mechanics", "mechanical force"], 3),
    (["self-organization", "self-organiz"], 3),
    (["gene circuit", "genetic circuit", "synthetic circuit"], 3),
    (["foundation model", "virtual cell", "AI cell biology"], 3),
    # Secondary topics — moderate value
    (["organoid", "lumenogenesis", "lumen formation", "lumenoid"], 3),
    (["stem cell", "iPSC", "pluripotent", "hiPSC"], 2),
    (["bioelectricity", "bioelectric", "membrane voltage"], 2),
    (["spatial transcriptomics", "spatial biology", "spatial cell"], 2),
    (["tissue fluidity", "solid-fluid", "fluid-solid"], 2),
    (["Turing pattern", "reaction-diffusion", "reaction diffusion"], 2),
    (["phase separation", "condensate", "biomolecular condensate"], 2),
    (["collective migration", "collective cell"], 2),
    (["multicellular", "multi-cellular"], 2),
    (["live-cell imaging", "live cell imaging", "live imaging", "morphodynamics"], 2),
    (["image-based profiling", "cell painting", "phenomics", "high-content imaging"], 2),
    (["disease model", "hypertrophic cardiomyopathy", "HCM", "myosin mutation"], 1),
    (["cell-to-cell variation", "cell-to-cell variability", "single-cell heterogeneity"], 2),
    (["cell-cell communication", "intercellular signaling", "paracrine", "juxtacrine", "cell interaction network", "ligand-receptor"], 3),
    (["developmental biology", "gene regulatory network", "lineage specification", "embryonic patterning", "transcription factor cascade", "cell lineage", "embryo model", "gastruloid"], 3),
    # Lower-weight topics
    (["single-cell", "single cell omics", "scRNA"], 1),
    (["patterning", "tissue patterning", "developmental patterning"], 1),
    (["development", "developmental biology"], 1),
    (["cell state", "cell identity"], 1),
    (["machine learning", "deep learning", "neural network"], 1),
    (["WNT", "Wnt signaling", "beta-catenin"], 1),
]

# Tracked author names — finding any of these adds points
_TRACKED_AUTHORS = [
    # Cell Science core
    "Gunawardane", "Rafelski", "Gerbin", "Viana", "Johnson",
    # Collaborators
    "Theriot",
    # Synthetic dev bio
    "Morsut", "Elowitz", "Ebisuya", "Bintu",
    # Morphogenesis / mechanics
    "Zernicka-Goetz", "Liberali", "Wickstrom", "Hannezo", "Petridou", "Streichan", "Priya",
    # Signaling
    "Toettcher", "Tsai", "Garcia-Ojalvo",
    # Bioelectricity
    "Levin",
]

# High-impact journals add a point
_TOP_JOURNALS = [
    "Nature", "Nature Cell Biology", "Nature Methods", "Nature Communications",
    "Nature Biotechnology", "Nature Reviews Molecular Cell Biology",
    "Cell", "Cell Systems", "Cell Reports Methods", "Cell Stem Cell", "Cell Reports",
    "Science", "eLife", "Developmental Cell", "Development",
    "PLOS Computational Biology", "Molecular Biology of the Cell", "Biophysical Journal",
    "Annual Review of Cell and Developmental Biology",
]

# Relevance note templates — matched in priority order, top 2 are joined
_RELEVANCE_NOTES = [
    (["cell decision", "cell fate decision", "bistability", "stochastic switching", "signal integration threshold"],
     "Directly addresses the top-priority question of how cells make decisions — bistability, signal integration, and stochastic switching are central to understanding cell identity and fate."),
    (["lumen morphogenesis", "lumenoid", "lumen pressure", "lumen mechanics", "hydraulic lumen"],
     "Directly relevant to lumen morphogenesis and lumenoid systems — a top priority covering how pressure, osmotic forces, and shape mechanics drive lumen formation across tissue types."),
    (["novel method", "new method", "experimental design", "imaging platform", "microscopy method", "biosensor"],
     "Introduces a novel experimental method or platform — very high priority given strong interest in how experiments are designed and what new biological questions they make tractable."),
    (["endogenous tag", "mEGFP", "knock-in fluorescent", "CRISPR tag hiPSC"],
     "Directly aligned with the Allen Cell Collection's CRISPR/mEGFP endogenous-tagging approach for quantitative live imaging of organelles in hiPSCs."),
    (["intracellular organization", "organelle positioning", "organelle variation"],
     "Directly addresses Cell Science's program on intracellular organization — how organelles are coordinated within cells and why genetically identical cells differ structurally."),
    (["holistic cell state", "cell state imaging morphology"],
     "Supports the core Cell Science thesis that cell state requires integrating structural organization and morphology alongside gene expression data."),
    (["hiPSC cardiomyocyte", "iPSC-CM", "cardiomyocyte maturation", "sarcomere"],
     "Relevant to hiPSC-derived cardiomyocyte biology and quantitative structural imaging of cardiac cells."),
    (["synthoid", "synthetic cell community", "CellScapes"],
     "Core to Cell Science's CellScapes initiative — the 10-year program to build programmable synthetic cell communities (synthoids) to study how cells cooperate to form tissues."),
    (["morpho-dynamic", "morphodynamic phenotype", "phenotype-genotype coupling"],
     "Relevant to Cell Science's morphodynamic phenotyping program, which treats live-imaging data as a high-dimensional readout of cell state and genotype."),
    (["virtual cell", "generative cell model", "VAE cell morphology"],
     "Supports Cell Science's virtual cell and generative modeling agenda for integrating multi-modal cell biology data into predictive computational models."),
    (["cell-cell communication", "intercellular signaling", "paracrine", "juxtacrine", "cell interaction network", "ligand-receptor"],
     "Directly relevant to understanding how cells send and receive signals from neighbors — foundational for collective cell decision-making and multicellular coordination, both core Cell Science themes."),
    (["developmental biology", "gene regulatory network", "lineage specification", "embryonic patterning", "transcription factor cascade", "cell lineage", "embryo model", "gastruloid"],
     "Directly relevant to Cell Science's foundational interest in how cells acquire and maintain identity — gene regulatory networks, lineage specification, and embryonic patterning are central to understanding cell decision-making and fate in developmental contexts."),
    (["disease model", "hypertrophic cardiomyopathy", "HCM", "myosin mutation"],
     "Tangentially relevant to disease modeling using hiPSC lines."),
    (["cell-to-cell variation", "cell-to-cell variability", "single-cell heterogeneity", "cellular heterogeneity"],
     "Directly addresses Cell Science's core question of why genetically identical cells differ structurally and how variation encodes functional information."),
    (["morphogenesis", "tissue morphogenesis", "morphogenetic", "tissue formation", "morpholog"],
     "Relevant to Cell Science's interest in tissue self-organization, emergent patterning, and the physical principles shaping biological structures."),
    (["synthetic biology", "synthetic developmental", "synthetic cell", "synthetic morpholog"],
     "Aligned with the CellScapes program and Cell Science's engagement with synthetic developmental biology — engineering gene circuits to program cell community behavior."),
    (["cell fate", "fate decision", "fate transition"],
     "Relevant to Cell Science's interest in how cells make identity decisions, with implications for stem cell differentiation and iPSC-based model systems."),
    (["mechanobiology", "tissue mechanics", "mechanical force", "biophysical force", "biophysical", "mechanical constraint", "mechanical determinant"],
     "Supports Cell Science's interest in tissue mechanics and how physical forces govern cell behavior, tissue organization, and morphogenesis."),
    (["self-organization", "self-organiz"],
     "Relevant to Cell Science's interest in emergent tissue organization and how multicellular systems self-pattern without external instruction."),
    (["gene circuit", "genetic circuit", "synthetic circuit", "optogenetic", "light-responsive"],
     "Aligned with CellScapes' use of engineered gene circuits to program synthetic cell communities toward controlled tissue-level behaviors."),
    (["foundation model", "AI cell biology", "systems biology", "artificial intelligence"],
     "Relevant to Cell Science's AI and computational agenda for modeling cell biology and building virtual cell frameworks."),
    (["organoid", "lumenogenesis", "lumen formation", "lumenoid", "lumen"],
     "Relevant to lumen morphogenesis, lumenoid self-organization, organoid systems, and live imaging of three-dimensional culture morphodynamics."),
    (["stem cell", "iPSC", "pluripotent", "hiPSC"],
     "Relevant to Cell Science's core work on hiPSC biology, pluripotent stem cell engineering, and stem cell-derived model systems."),
    (["bioelectricity", "bioelectric", "membrane voltage"],
     "Touches on bioelectric signaling mechanisms relevant to Cell Science's broader interest in non-canonical developmental signals in morphogenesis."),
    (["spatial transcriptomics", "spatial biology", "spatial cell"],
     "Supports the multimodal view of cell state central to Cell Science, connecting tissue organization and spatial context with molecular identity."),
    (["tissue fluidity", "solid-fluid", "fluid-solid", "tissue rigidity", "phase transition", "rigidity"],
     "Relevant to Cell Science's interest in tissue mechanics and phase-like transitions that govern how tissues flow or stiffen during morphogenesis."),
    (["Turing pattern", "reaction-diffusion", "reaction diffusion"],
     "Relevant to Cell Science's interest in self-organizing systems and the reaction-diffusion dynamics underlying biological patterning."),
    (["phase separation", "condensate", "biomolecular condensate", "polymer concept", "polymer physic"],
     "Relevant to understanding how biomolecular condensates and polymer organization contribute to intracellular structure — a core Cell Science research interest."),
    (["collective migration", "collective cell"],
     "Relevant to Cell Science's interest in collective cell behaviors, emergent tissue dynamics, and the mechanics of coordinated cell movement."),
    (["multicellular", "multi-cellular"],
     "Relevant to CellScapes and Cell Science's broader interest in how cells cooperate and self-organize to form tissues with emergent properties."),
    (["live-cell imaging", "live cell imaging", "live imaging", "morphodynamics"],
     "Directly relevant to Cell Science's live-cell imaging platforms for morphodynamic phenotyping and organelle dynamics at scale."),
    (["image-based profiling", "cell painting", "phenomics", "high-content imaging"],
     "Relevant to Cell Science's phenomics approach, which uses high-content imaging as a high-dimensional readout of cell state and function."),
    (["spatial transcriptomics", "spatial biology"],
     "Supports Cell Science's multimodal cell state program by linking molecular identity to spatial tissue context."),
    (["single-cell", "single cell omics", "scRNA"],
     "Relevant to Cell Science's multimodal view of cell state, where single-cell molecular data is integrated with structural and morphological measurements."),
    (["WNT", "Wnt signaling", "beta-catenin"],
     "Relevant to Cell Science's interest in key developmental pathways governing organoid patterning and stem cell differentiation."),
    (["patterning", "tissue patterning", "developmental patterning", "pattern formation"],
     "Relevant to Cell Science's interest in how spatial patterns emerge during development from molecular and cellular interactions."),
    (["machine learning", "deep learning", "neural network"],
     "Relevant to Cell Science's AI agenda for cell segmentation, morphology modeling, and predicting cell state from multi-modal imaging data."),
    (["cell state", "cell identity", "cell signalling", "cell signaling", "temporal signall", "signalling"],
     "Relevant to Cell Science's holistic cell state program, which integrates molecular, structural, and morphological data to define cell identity."),
    (["development", "developmental biology", "molecular cell biology", "cellular function"],
     "Relevant to Cell Science's foundational interest in how cells and tissues build organisms through coordinated developmental programs."),
]


def _keyword_score(paper: dict) -> dict:
    """Simple keyword + author heuristic used when no Anthropic key is available."""
    text = ((paper.get("title") or "") + " " + (paper.get("abstract") or "")).lower()
    authors = " ".join(str(a) for a in (paper.get("authors") or []))
    journal = paper.get("journal", "") or ""
    abstract = (paper.get("abstract") or "").strip()

    points = 0
    matched_tags = []
    relevance_parts = []

    for keywords, pts in _KEYWORD_RULES:
        if any(kw.lower() in text for kw in keywords):
            points += pts
            matched_tags.append(keywords[0])

    for keywords, note in _RELEVANCE_NOTES:
        if any(kw.lower() in text for kw in keywords):
            relevance_parts.append(note)
            if len(relevance_parts) >= 2:
                break

    for author in _TRACKED_AUTHORS:
        if author.lower() in authors.lower():
            points += 2
            break

    if any(j.lower() in journal.lower() for j in _TOP_JOURNALS):
        points += 1

    # Normalise to 0-10 (raw points cap at ~15 for a perfect paper)
    score = min(10, round(points * 10 / 12))

    tags = [t for t in KNOWN_TAGS if t.lower() in text]

    pub_type = paper.get("pub_type", "research")

    author_list = paper.get("authors", [])
    author_str = ", ".join(str(a) for a in author_list[:6])
    if len(author_list) > 6:
        author_str += " et al."

    relevance = " ".join(relevance_parts)

    existing_summary = paper.get("summary", "")
    if not existing_summary and abstract:
        sentences = re.split(r'(?<=[.!?])\s+', abstract)
        summary = " ".join(sentences[:3])
    else:
        summary = existing_summary

    paper_out = dict(paper)
    paper_out.update({
        "authors": author_str,
        "year": str(paper.get("year", "")) if paper.get("year") else "",
        "score": score,
        "summary": summary,
        "relevance": relevance,
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

    prompt = f"""You are helping curate a research paper reading list for the Allen Institute for Cell Science.

Background on research interests:
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
  "summary": "<3-5 sentences: what this paper does and why it matters scientifically. Write for a science-savvy executive. Do not reference any individual by name. Empty string if insufficient info.>",
  "relevance": "<1-2 sentences on why this paper is specifically relevant to Cell Science research priorities (quantitative imaging, cell state, stem cell biology, morphogenesis, synthetic biology, CellScapes/synthoids). Be concrete. Empty string if not clearly relevant.>",
  "tags": "<comma-separated subset of: {tags_list} — topic tags only, NEVER use author names, lab names, or paper types (research/review/perspective)>",
  "type": "<research | review | perspective>",
  "reasoning": "<1 sentence explaining the score>"
}}

Scoring guide:
- 9-10: Directly on core topics, from a high-impact journal, clear Cell Science relevance
- 7-8: Relevant to ≥2 interest areas, or from a tracked author/lab
- 5-6: Tangentially relevant, interesting but lower priority
- 0-4: Not relevant to Cell Science interests

Hard caps — score these LOW regardless of keyword matches:
- Cardiac / cardiomyocyte biology (HCM, cardiomyopathy, sarcomere, iPSC-CM): ≤3 unless genuinely novel method applicable beyond cardiac
- Neuroscience / neural (neural organoids, brain, neurodegeneration, cortex): ≤2 unless method is broadly applicable to non-neural cell biology
- Non-mammalian systems (plant, yeast, C. elegans, Drosophila, zebrafish): ≤4 unless novel method with clear mammalian applicability
- Purely clinical or translational (epidemiology, patient cohorts, clinical trials, disease treatment): ≤2"""

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
        "relevance": result.get("relevance", ""),
        "tags": result.get("tags", ""),
        "type": result.get("type", pub_type),
        "reasoning": result.get("reasoning", ""),
    })
    return paper_out
