# Literature Agent for Ru Gunawardane

Automated agent that discovers new biology research papers aligned with Ru's interests,
scores their relevance using Claude, and adds qualifying papers to the
[Smartsheet paper repository](https://app.smartsheet.com/sheets/4q444224J9c8pcpGj9MVHQxC76Gq5fccGMg673M1).

## What it does

1. **Searches** Semantic Scholar, bioRxiv, and PubMed for papers published in the last N days
2. **Deduplicates** against papers already in the Smartsheet
3. **Scores** each candidate 0–10 using Claude, with a rich prompt grounded in Ru's specific interests
4. **Adds** papers scoring ≥7 to the Smartsheet with Status = "On deck for Ru"

### Topics covered

- Morphogenesis & tissue mechanics
- Synthetic developmental biology (gene circuits, programming cell fate)
- Cell fate decisions & signaling dynamics
- Self-organization in multicellular systems
- Organoids, lumenogenesis, 3D tissue models
- AI/ML in cell biology (foundation models, virtual cells)
- Bioelectricity in development
- Spatial transcriptomics & single-cell biology

### Tracked authors

Papers by these researchers are always caught regardless of query match:
Leonardo Morsut, Michael Elowitz, Magda Zernicka-Goetz, Prisca Liberali, Michael Levin,
Sara Wickstrom, Edouard Hannezo, Miki Ebisuya, Nicoletta Petridou, Sebastian Streichan,
Rashmi Priya, Jared Toettcher, Lacra Bintu, Jordi Garcia-Ojalvo, Tony Tsai.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/ismi-ops/literature-rg.git
cd literature-rg
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in:
#   SMARTSHEET_API_KEY — from Account > Personal Settings > API Access in Smartsheet
#   ANTHROPIC_API_KEY  — from console.anthropic.com
```

### 3. Run

```bash
# Default: last 14 days, minimum score 7
python agent.py

# Adjust lookback window and threshold
python agent.py --days 30 --min-score 6

# Preview results without writing to Smartsheet
python agent.py --dry-run
```

## GitHub Actions (automated weekly runs)

The workflow at `.github/workflows/run_agent.yml` runs every Monday at 9 AM UTC.

To enable it, add two repository secrets:
- `SMARTSHEET_API_KEY`
- `ANTHROPIC_API_KEY`

Go to **Settings → Secrets and variables → Actions → New repository secret** for each.

You can also trigger a run manually from the **Actions** tab with custom `--days`, `--min-score`,
and `--dry-run` inputs.

## Configuration

Edit `src/config.py` to:
- Add/remove **search queries** (`SEARCH_QUERIES`, `PUBMED_QUERIES`)
- Add/remove **tracked authors** (`TRACKED_AUTHORS`)
- Update the **relevance context** (`RELEVANCE_CONTEXT`) as Ru's interests evolve
- Add new **tags** to the vocabulary (`KNOWN_TAGS`)

## Project structure

```
agent.py                  Main entry point
src/
  config.py               Search queries, author list, Smartsheet IDs, relevance context
  relevance.py            Claude-based scoring and summary generation
  smartsheet_client.py    Smartsheet REST API read/write
  sources/
    semantic_scholar.py   Semantic Scholar API (primary source)
    biorxiv.py            bioRxiv preprint API
    pubmed.py             PubMed E-utilities API
.github/workflows/
  run_agent.yml           Weekly GitHub Actions schedule
```
