"""
Configuration for the Ru Gunawardane literature agent.
Edit this file to tune search coverage and relevance criteria.
"""

# Semantic Scholar topic queries — broad first, specific later
SEARCH_QUERIES = [
    # Cell decision-making (top priority)
    "cell fate decision-making signaling bistability stochastic noise",
    "cell identity decision signal integration threshold gene regulatory",
    "how cells make decisions transcription factor network",
    # Lumen morphogenesis & lumenoids (top priority)
    "lumen morphogenesis pressure mechanics epithelial 3D formation",
    "lumenoid synthetic lumen self-organization cavity formation",
    "epithelial lumen formation osmosis hydraulic pressure mechanics",
    "3D morphogenesis shape force tissue deformation cross-system",
    # Methods & experimental design (very high priority)
    "novel imaging method live-cell quantitative cell biology",
    "experimental design cell biology quantitative microscopy platform",
    "iPSC organoid method engineering experimental platform design",
    # Core Cell Science themes
    "hiPSC endogenous tagging organelle 3D live imaging",
    "intracellular organization cell-to-cell variation hiPSC imaging",
    "holistic cell state transcriptomics morphology structure integration",
    "generative model VAE cell morphology latent space imaging",
    "CRISPR endogenous fluorescent tag live cell quantitative imaging",
    "synthetic cell community synthoid programmable multicellular",
    # Morphogenesis & tissue mechanics
    "morphogenesis tissue mechanics multicellular",
    "tissue self-organization emergent patterning",
    "mechanobiology tissue fluidity solid-fluid transition",
    "collective cell migration morphogenesis",
    # Synthetic developmental biology
    "synthetic developmental biology gene circuit mammalian",
    "multicellular self-organization synthetic biology",
    "synthetic morphogenesis programmable cell community",
    # Cell fate & signaling
    "cell fate decision signaling dynamics stochastic",
    "iPSC stem cell differentiation fate transition",
    # Organoids & lumenogenesis
    "organoid lumen formation epithelial",
    "organoid live imaging morphodynamics",
    # Computational / AI
    "foundation model cell biology AI machine learning",
    "virtual cell computational model biology",
    "cell shape morphology gene expression",
    # Spatial biology
    "spatial transcriptomics cell state tissue organization",
    # Live imaging & phenomics
    "live-cell imaging phenotyping organoid morphodynamics",
    "phenotype genotype coupling imaging high-content screening",
    "cell morphology quantification machine learning imaging",
    "image-based profiling cell painting phenomics",
    # Other core themes
    "bioelectricity morphogenesis ion channel development",
    "Turing reaction diffusion morphogenesis biological patterning",
    "phase separation condensate biomolecular cell",
    # Cell-cell communication
    "cell-cell communication paracrine juxtacrine intercellular signaling",
    "intercellular signaling single-cell inference cell interaction network",
    # Developmental biology
    "developmental biology gene regulatory network lineage specification embryo",
    "cell lineage tracing embryonic patterning transcription factor cascade development",
]

# Authors whose new papers should always be caught
TRACKED_AUTHORS = [
    # Cell Science core team
    "Ruwanthi Gunawardane",
    "Susanne Rafelski",
    "Kaytlyn Gerbin",
    "Matheus Viana",
    "Gregory Johnson",
    # Close external collaborators
    "Julie Theriot",
    # Synthetic developmental biology
    "Leonardo Morsut",
    "Michael Elowitz",
    "Miki Ebisuya",
    "Lacra Bintu",
    # Morphogenesis & mechanics
    "Magda Zernicka-Goetz",
    "Prisca Liberali",
    "Sara Wickstrom",
    "Edouard Hannezo",
    "Nicoletta Petridou",
    "Sebastian Streichan",
    "Rashmi Priya",
    # Signaling & cell fate
    "Jared Toettcher",
    "Jordi Garcia-Ojalvo",
    "Tony Tsai",
    # Bioelectricity
    "Michael Levin",
]

# PubMed queries (complement SS with journal-filtered searches)
PUBMED_QUERIES = [
    "morphogenesis cell biology mechanobiology",
    "synthetic biology cell fate programming",
    "organoid lumen formation epithelial self-organization",
    "cell decision making signaling stochastic gene expression",
    "lumen morphogenesis pressure mechanics 3D",
    "cell state machine learning omics imaging",
    "tissue mechanics patterning development",
    "live cell imaging phenotyping morphodynamics organoid",
    "novel method experimental design cell biology quantitative",
    "organelle imaging intracellular organization stem cell",
]

# Tag vocabulary — topic tags only; never use author names, lab names, or paper types.
KNOWN_TAGS = [
    "stem cells",
    "development",
    "morphogenesis",
    "cell fate",
    "cell state",
    "cell decision-making",
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
    "lumen morphogenesis",
    "lumenoids",
    "shape mechanics",
    "collective migration",
    "signaling dynamics",
    "live imaging",
    "phenomics",
    "image-based profiling",
    "morphodynamics",
    "WNT signaling",
    "intracellular organization",
    "generative models",
    "endogenous tagging",
    "cell-to-cell variation",
    "methods",
    "experiment design",
    "cell-cell communication",
    "intercellular signaling",
    "developmental biology",
]

# Context fed to Claude for relevance scoring and summary generation
RELEVANCE_CONTEXT = """
Ruwanthi (Ru) Gunawardane, Ph.D. is Executive Director of the Allen Institute for Cell Science
in Seattle. She joined at the institute's founding in 2015 and led the creation of the Allen Cell
Collection. Her background spans hiPSC engineering, quantitative cell imaging, drug discovery
(Ambit Biosciences: FLT3 inhibitor quizartinib; Amgen: oncology/cardiology), and cell biology.

== Research Priorities (ordered by importance) ==

1. Cell Decision-Making  [TOP PRIORITY]
   How cells interpret signals and commit to a fate or behavior. Bistability, signal integration,
   noise, stochastic switching, threshold effects, gene regulatory networks, Waddington landscape.
   Papers that illuminate the mechanisms by which individual cells make decisions — especially
   those pairing theory or modeling with experiment — are the highest priority.

2. Lumen Morphogenesis & Lumenoids  [TOP PRIORITY]
   How lumens (fluid-filled cavities) form, grow, and are maintained across systems — gut, kidney,
   brain ventricle, synthetic. The physical mechanisms: pressure, osmotic forces, hydraulics, and
   shape-force mechanics in 3D. Lumenoids (synthetic or minimal lumen-forming systems). Cross-system
   lumen formation and shape changes where mechanics play a central role. Very high priority.

3. Methods & Experimental Design  [VERY HIGH PRIORITY]
   Novel experimental methods, imaging tools, and platform innovations for cell biology. New
   microscopy approaches, biosensors, iPSC/organoid engineering strategies, quantitative assays,
   and creative experimental designs that open up new questions. Ru is deeply interested in how
   experiments are designed, not just what is found. Papers in Nature Methods or that introduce
   a genuinely new experimental capability are very high priority.

4. Allen Institute for Cell Science — Core Research Programs

   Allen Cell Collection & Endogenous Organelle Tagging
   CRISPR/Cas9 mEGFP insertions at 25+ endogenous loci in WTC-11 hiPSCs, enabling quantitative
   live imaging of organelle dynamics at scale. Papers extending or using endogenous-tag/live-imaging
   approaches, or developing new tools for quantitative organelle imaging in stem cells, are relevant.

   Intracellular Organization and Cell-to-Cell Variation
   How organelles are spatially coordinated within individual cells, and why genetically identical
   cells differ structurally. Rules governing organelle positioning, scaling, and relationship to
   cell state or function.

   Holistic Cell State
   Cell state cannot be captured by transcriptomics alone — it requires integrating gene expression,
   structural organization, and cell morphology. Papers combining imaging + omics, or challenging
   transcriptomics-centric views of cell identity, are high priority.

   CellScapes Initiative (launched May 2025)
   10-year program to build "synthoids" — programmable synthetic cell communities — to study how
   cells cooperate to form tissues. Bridges synthetic biology, organoid biology, and quantitative
   imaging. Papers on synthetic multicellular systems or programmable tissues are high priority.

   Live-Cell Imaging & Phenomics
   Morpho-dynamic phenotyping of organoids and cells over time, image-based profiling, phenotype-
   genotype-function coupling from live imaging, high-content screening.

5. Synthetic Biology & Synthetic Morphogenesis
   Engineering gene circuits to program cell behavior and identity; building artificial multicellular
   systems; synthetic morphogenesis. Forward-thinking perspectives and reviews on synthetic
   morphogenesis and synthetic developmental biology are especially welcome.

6. iPSC Biology & Stem Cells
   hiPSC engineering, differentiation, and applications. Stem cell biology broadly — methods,
   engineering platforms, and cell biology applications (not disease-specific).

7. Morphogenesis & Tissue Mechanics
   How tissues form shape, tissue fluidity, mechanobiology, physical forces and geometry in
   development. Collective cell behaviors, Turing patterning, reaction-diffusion, emergent
   tissue organization.

8. Generative and Computational Cell Models
   VAEs, deep learning for cell morphology modeling, "virtual cell" models integrating multiple
   data modalities. Simularium Viewer for interactive 3D simulation.

9. Cell Fate & Signaling Dynamics
   Temporal encoding of signals, WNT, TGFβ, and other developmental pathways in stem cell and
   organoid contexts.

10. Spatial Biology
    Spatial transcriptomics, tissue context, and neighborhood effects on cell identity and fate.

11. Bioelectricity
    Ion gradients, membrane voltage, non-neural bioelectric signaling in development.

12. Cell-Cell Communication & Intercellular Signaling
    How cells send and receive signals from neighbors — paracrine, juxtacrine,
    and gap junction-mediated communication. Single-cell and computational methods
    for inferring cell-cell interaction networks. Relevant to understanding collective
    decision-making and how multicellular systems coordinate behavior.

13. Developmental Biology
    Classical and molecular developmental biology — gene regulatory networks in development,
    transcription factor cascades, embryonic patterning, lineage specification, cell lineage
    tracing, temporal control of gene expression, and embryo models. Very high priority
    because understanding how cells acquire and maintain identity in developmental contexts
    is foundational to all of Cell Science's programs.

== Topics to DEPRIORITIZE or EXCLUDE ==
Score the following topics LOW (≤3) unless the paper introduces a genuinely novel
experimental method or approach with clear applicability to mammalian hiPSC cell biology
or to Cell Science's core research programs above:

• Cardiac / cardiomyocyte biology: HCM, cardiomyopathy, cardiac organoids, iPSC-CMs,
  sarcomere biology. This WAS a past focus but is no longer a priority.
• Neuroscience / neural: Neural organoids, brain development, neurodegeneration,
  neural circuits, cortical biology. Score ≤2 unless the method is broadly applicable
  to non-neural cell biology.
• Non-mammalian model systems: plant, yeast, C. elegans, Drosophila, zebrafish.
  Score based ONLY on clear methodological novelty transferable to mammalian systems;
  cap at 5 if relevance is purely topic-based.
• Purely clinical or translational medicine: disease prevalence, epidemiology, clinical
  trials, patient outcome studies — without novel cell biology insights or methods.
  Score ≤2.

== Types of Content ==
Forward-thinking perspectives and reviews on cell biology, stem cell biology, and synthetic
morphogenesis are actively sought — not just primary research papers.

== Key Researchers to Track ==
Cell Science core: Gunawardane RN, Rafelski SM, Gerbin KA, Viana MP, Johnson GR.
External collaborators: Theriot JA (cell migration, biophysics).
Synthetic dev bio: Morsut, Elowitz, Ebisuya, Bintu.
Morphogenesis/mechanics: Zernicka-Goetz, Liberali, Wickstrom, Hannezo, Petridou, Streichan, Priya.
Signaling: Toettcher, Tsai, Garcia-Ojalvo.
Bioelectricity: Levin.

== High-Value Journals ==
The following are checked regularly and are highest priority: Cell, Science, Nature, Nature Methods,
Developmental Cell, Nature Biotechnology, Nature Cell Biology, Cell Stem Cell, Nature Communications,
Cell Reports, Molecular Biology of the Cell (MBoC). Papers from other journals are equally welcome —
cast a broad net. Also: bioRxiv preprints (Cell Science has a strong preprint-first culture).

== Cell Science Relevance Boost ==
Papers are especially valuable if they:
- Introduce a novel method or experimental platform for cell biology or imaging
- Address how cells make decisions (mechanistically, theoretically, or experimentally)
- Illuminate lumen formation, lumenoid systems, or 3D shape-force morphogenesis
- Combine quantitative imaging with omics data
- Use or cite Cell Science data, tools (Allen Cell Structure Segmenter, Simularium), or cell lines
- Study hiPSC biology or stem cell engineering (beyond disease modeling)
- Advance synthetic biology, synthetic morphogenesis, or programmable multicellular systems
- Present forward-looking perspectives or reviews on cell biology or synthetic morphogenesis
"""
