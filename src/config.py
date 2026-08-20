"""
Configuration for the Ru Gunawardane literature agent.
Edit this file to tune search coverage and relevance criteria.
"""

# Semantic Scholar topic queries — broad first, specific later
SEARCH_QUERIES = [
    "morphogenesis tissue mechanics multicellular",
    "synthetic developmental biology gene circuit mammalian",
    "cell fate decision signaling dynamics stochastic",
    "organoid lumen formation epithelial",
    "tissue self-organization emergent patterning",
    "bioelectricity morphogenesis ion channel development",
    "foundation model cell biology AI machine learning",
    "spatial transcriptomics cell state tissue organization",
    "mechanobiology tissue fluidity solid-fluid transition",
    "synthetic cell minimal life bottom-up reconstitution",
    "Turing reaction diffusion morphogenesis biological patterning",
    "iPSC stem cell differentiation fate transition",
    "phase separation condensate biomolecular cell",
    "collective cell migration morphogenesis",
    "virtual cell computational model biology",
    "multicellular self-organization synthetic biology",
    "cell shape morphology gene expression",
    "tissue architecture single-cell spatial",
    "live-cell imaging phenotyping organoid morphodynamics",
    "phenotype genotype coupling imaging high-content screening",
    "cell morphology quantification machine learning imaging",
    "organoid live imaging WNT signaling intestinal",
    "image-based profiling cell painting phenomics",
]

# Authors whose new papers should always be caught
TRACKED_AUTHORS = [
    "Leonardo Morsut",
    "Michael Elowitz",
    "Magda Zernicka-Goetz",
    "Prisca Liberali",
    "Michael Levin",
    "Sara Wickstrom",
    "Edouard Hannezo",
    "Miki Ebisuya",
    "Nicoletta Petridou",
    "Sebastian Streichan",
    "Rashmi Priya",
    "Jared Toettcher",
    "Lacra Bintu",
    "Jordi Garcia-Ojalvo",
    "Tony Tsai",
]

# PubMed queries (complement SS with journal-filtered searches)
PUBMED_QUERIES = [
    "morphogenesis cell biology mechanobiology",
    "synthetic biology cell fate programming",
    "organoid tissue self-organization epithelial",
    "cell state machine learning omics imaging",
    "tissue mechanics patterning development",
    "live cell imaging phenotyping morphodynamics organoid",
    "high-content imaging phenomics genotype phenotype",
]

# Tag vocabulary — topic tags only; never use author names, lab names, or paper types.
KNOWN_TAGS = [
    "stem cells",
    "development",
    "morphogenesis",
    "cell fate",
    "cell state",
    "self-organization",
    "synthetic biology",
    "gene circuits",
    "mechanobiology",
    "tissue mechanics",
    "morphology",
    "AI / ML",
    "single-cell",
    "multimodal",
    "spatial biology",
    "organoid",
    "multicellular",
    "Turing patterning",
    "phase separation",
    "bioelectricity",
    "synthetic morphogenesis",
    "virtual cell",
    "iPSC",
    "lumenogenesis",
    "collective migration",
    "signaling dynamics",
    "live imaging",
    "phenomics",
    "image-based profiling",
    "morphodynamics",
    "WNT signaling",
]

# Context fed to Claude for relevance scoring and summary generation
RELEVANCE_CONTEXT = """
Ru Gunawardane is Chief Science Officer at the Allen Institute for Cell Science (AICS).
Her research interests include:

1. Morphogenesis & Tissue Mechanics — how tissues form shape, tissue fluidity, fluid-solid
   phase transitions, mechanobiology, physical forces and geometry in development.

2. Synthetic Developmental Biology — engineering gene circuits, programming cell behavior and
   identity, building artificial multicellular systems. Key labs she follows: Elowitz, Morsut,
   Ebisuya, Church, Bintu.

3. Cell Fate & Cell State — how cells make identity decisions, signaling dynamics (especially
   temporal encoding), Waddington landscape framing, stochastic cell fate, heterogeneity.

4. Self-Organization — Turing patterning, reaction-diffusion, emergent tissue properties from
   simple cellular rules, minimal component sets for patterning and morphogenesis.

5. Organoids & 3D Tissue Models — lumenogenesis, iPSC-based models, epithelial architecture,
   3D tissue self-assembly.

6. AI/ML in Cell Biology — foundation models for cells, virtual cell models, multimodal
   integration of omics and imaging data, computational approaches to cell identity.

7. Bioelectricity — ion gradients, membrane voltage, non-neural bioelectric signaling in
   development (Michael Levin's intellectual territory).

8. Spatial Biology — spatial transcriptomics, how cell identity relates to tissue context
   and neighborhood, spatial organization of cell fate.

9. Live-Cell Imaging & Phenomics — morpho-dynamic phenotyping of organoids and cells,
   image-based profiling (e.g. Cell Painting), phenotype-genotype-function coupling from
   live imaging, high-content screening, tools that treat imaging data as an image-"transcriptome"
   (e.g. SPOT/SAM frameworks), label-free live imaging at scale, integration of imaging with
   scRNA-seq. AICS has deep expertise in quantitative cell imaging; papers that advance the
   measurement or interpretation of cell/organoid morphodynamics are especially relevant.

Key researchers she tracks: Leonardo Morsut, Michael Elowitz (Elowitz lab), Magda Zernicka-Goetz,
Prisca Liberali, Michael Levin, Sara Wickstrom, Edouard Hannezo, Miki Ebisuya, Nicoletta Petridou,
Sebastian Streichan, Rashmi Priya, Jared Toettcher, Lacra Bintu.

High-value journals: Nature Cell Biology, Nature Reviews Molecular Cell Biology, Cell Systems,
Cell, Nature Communications, Nature Biotechnology, Development, Developmental Cell, eLife,
Science, Nature, Annual Review of Cell and Developmental Biology, Cell Reports Methods.

AICS context: The institute uses quantitative imaging, iPSCs, and computational modeling to
study cell structure and behavior. Papers that use AICS data/tools, cite AICS work, or directly
address questions about cell morphology, cell state, or how structure determines function are
especially valuable.
"""
