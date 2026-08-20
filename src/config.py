"""
Configuration for the Ru Gunawardane literature agent.
Edit this file to tune search coverage and relevance criteria.
"""

# Semantic Scholar topic queries — broad first, specific later
SEARCH_QUERIES = [
    # Core Cell Science themes
    "hiPSC endogenous tagging organelle 3D live imaging",
    "intracellular organization cell-to-cell variation hiPSC imaging",
    "holistic cell state transcriptomics morphology structure integration",
    "generative model VAE cell morphology latent space imaging",
    "CRISPR endogenous fluorescent tag live cell quantitative imaging",
    "hiPSC cardiomyocyte sarcomere maturation disease modeling",
    "hypertrophic cardiomyopathy myosin CRISPR stem cell",
    "synthetic cell community synthoid programmable multicellular",
    # Morphogenesis & tissue mechanics
    "morphogenesis tissue mechanics multicellular",
    "tissue self-organization emergent patterning",
    "mechanobiology tissue fluidity solid-fluid transition",
    "collective cell migration morphogenesis",
    # Synthetic developmental biology
    "synthetic developmental biology gene circuit mammalian",
    "multicellular self-organization synthetic biology",
    "synthetic cell minimal life bottom-up reconstitution",
    # Cell fate & signaling
    "cell fate decision signaling dynamics stochastic",
    "iPSC stem cell differentiation fate transition",
    # Organoids
    "organoid lumen formation epithelial",
    "organoid live imaging WNT signaling intestinal",
    # Computational / AI
    "foundation model cell biology AI machine learning",
    "virtual cell computational model biology",
    "cell shape morphology gene expression",
    # Spatial biology
    "spatial transcriptomics cell state tissue organization",
    "tissue architecture single-cell spatial",
    # Live imaging & phenomics
    "live-cell imaging phenotyping organoid morphodynamics",
    "phenotype genotype coupling imaging high-content screening",
    "cell morphology quantification machine learning imaging",
    "image-based profiling cell painting phenomics",
    # Other core themes
    "bioelectricity morphogenesis ion channel development",
    "Turing reaction diffusion morphogenesis biological patterning",
    "phase separation condensate biomolecular cell",
    "tissue architecture single-cell spatial",
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
    "organoid tissue self-organization epithelial",
    "cell state machine learning omics imaging",
    "tissue mechanics patterning development",
    "live cell imaging phenotyping morphodynamics organoid",
    "high-content imaging phenomics genotype phenotype",
    "hiPSC cardiomyocyte disease model CRISPR sarcomere",
    "organelle imaging intracellular organization stem cell",
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
    "cardiomyocyte",
    "intracellular organization",
    "generative models",
    "endogenous tagging",
    "disease modeling",
    "cell-to-cell variation",
]

# Context fed to Claude for relevance scoring and summary generation
RELEVANCE_CONTEXT = """
Ruwanthi (Ru) Gunawardane, Ph.D. is Executive Director of the Allen Institute for Cell Science
in Seattle. She joined at the institute's founding in 2015 and led the creation of the Allen Cell
Collection. Her background spans hiPSC engineering, quantitative cell imaging, drug discovery
(Ambit Biosciences: FLT3 inhibitor quizartinib; Amgen: oncology/cardiology), and cell biology.

== Allen Institute for Cell Science — Core Research Programs ==

1. Allen Cell Collection & Endogenous Organelle Tagging
   Cell Science's flagship resource: CRISPR/Cas9 mEGFP insertions at 25+ endogenous loci in WTC-11 hiPSCs,
   enabling quantitative live imaging of organelle dynamics at scale. Over 200,000 live-cell images
   openly available. Papers that extend or use this type of endogenous-tag/live-imaging approach,
   or that develop new tools for quantitative organelle imaging in stem cells, are very relevant.

2. Intracellular Organization and Cell-to-Cell Variation
   How organelles are spatially coordinated within individual cells, and why genetically identical
   cells differ structurally. Key questions: what rules govern organelle positioning and scaling?
   What is the relationship between structural variation and cell state or function?

3. Holistic Cell State
   A central Cell Science thesis: cell state cannot be captured by transcriptomics alone — it requires
   integrating gene expression, structural organization, and cell morphology. Papers that combine
   imaging + omics, or that challenge/support transcriptomics-centric views of cell identity, are
   especially high priority.

4. hiPSC-Derived Cardiomyocytes & Disease Modeling
   Cell Science has released six HCM (hypertrophic cardiomyopathy) hiPSC lines with CRISPR-introduced
   myosin mutations. Research on hiPSC-CM differentiation, sarcomere maturation, structural
   maturation benchmarks, and cardiac disease modeling (especially using stem cell lines and
   quantitative imaging) is directly relevant.

5. Generative and Computational Cell Models
   VAEs, conditional autoencoders, and deep learning for cell segmentation (Allen Cell Structure
   Segmenter), morphology modeling, and predicting cell state from structure. "Virtual cell" models
   that integrate multiple data modalities. Simularium Viewer for interactive 3D simulation.

6. CellScapes Initiative (launched May 2025)
   10-year program to build "synthoids" — programmable synthetic cell communities — to study how
   cells cooperate to form tissues. Bridges synthetic biology, organoid biology, and quantitative
   imaging. Papers on synthetic multicellular systems, programmable tissues, or engineering cell
   communities are high priority.

7. Live-Cell Imaging & Phenomics
   Morpho-dynamic phenotyping of organoids and cells over time, image-based profiling, phenotype-
   genotype-function coupling from live imaging, high-content screening. Tools that treat imaging
   data as an image-"transcriptome" (e.g. SPOT/SAM frameworks), label-free live imaging at scale,
   integration of live imaging with scRNA-seq.

8. Morphogenesis & Tissue Mechanics
   How tissues form shape, tissue fluidity, fluid-solid phase transitions, mechanobiology, physical
   forces and geometry in development. Collective cell behaviors, Turing patterning, reaction-
   diffusion, emergent tissue organization.

9. Synthetic Developmental Biology
   Engineering gene circuits to program cell behavior and identity; building artificial multicellular
   systems. Key labs: Elowitz, Morsut, Ebisuya, Bintu. The CellScapes synthoid program is Cell Science's
   own entry into this space.

10. Cell Fate & Signaling Dynamics
    How cells make identity decisions, temporal encoding of signals, Waddington landscape, stochastic
    fate, heterogeneity. WNT, TGFβ, and other developmental pathways in stem cell and organoid
    contexts.

11. Spatial Biology
    Spatial transcriptomics, how cell identity relates to tissue context and neighborhood,
    spatial organization of cell fate.

12. Bioelectricity
    Ion gradients, membrane voltage, non-neural bioelectric signaling in development.

== Key Researchers to Track ==
Cell Science core: Gunawardane RN, Rafelski SM, Gerbin KA, Viana MP, Johnson GR.
External collaborators: Theriot JA (cell migration, biophysics).
Synthetic dev bio: Morsut, Elowitz, Ebisuya, Bintu.
Morphogenesis/mechanics: Zernicka-Goetz, Liberali, Wickstrom, Hannezo, Petridou, Streichan, Priya.
Signaling: Toettcher, Tsai, Garcia-Ojalvo.
Bioelectricity: Levin.

== High-Value Journals ==
Nature, Nature Cell Biology, Nature Methods, Nature Communications, Nature Biotechnology,
Nature Reviews Molecular Cell Biology, Cell, Cell Systems, Cell Reports Methods,
Science, eLife, Developmental Cell, Development,
Annual Review of Cell and Developmental Biology,
PLOS Computational Biology, Molecular Biology of the Cell, Biophysical Journal.
Also: bioRxiv preprints (Cell Science has a strong preprint-first culture).

== Cell Science Relevance Boost ==
Papers are especially valuable if they:
- Use or cite Cell Science data, tools (Allen Cell Structure Segmenter, Simularium), or cell lines
- Address how structure determines function in cells or tissues
- Combine quantitative imaging with omics data
- Develop tools for live-cell imaging, organelle segmentation, or morphology quantification
- Study hiPSC biology, cardiomyocyte differentiation, or stem cell engineering
- Advance "virtual cell" or generative cell modeling approaches
"""
