"""Generate index.html from papers.json."""
import json
from pathlib import Path

PAPERS_PATH = Path("papers.json")
OUTPUT_PATH = Path("index.html")


def build_html(papers: list[dict]) -> str:
    papers_json = json.dumps(papers, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ru's Reading List · AICS</title>
<style>
  :root {{
    --bg: #f8f9fb;
    --surface: #ffffff;
    --border: #e2e5ea;
    --text: #1a1d23;
    --muted: #6b7280;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --tag-bg: #f0f4ff;
    --tag-text: #3b4fc0;
    --chip-active-bg: #2563eb;
    --chip-active-text: #ffffff;
    --shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
    --shadow-hover: 0 4px 12px rgba(0,0,0,.12);
    --radius: 10px;
    --score-high: #16a34a;
    --score-mid: #ca8a04;
    --score-low: #6b7280;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1117;
      --surface: #1c1f27;
      --border: #2a2e38;
      --text: #e8eaf0;
      --muted: #9ca3af;
      --accent: #60a5fa;
      --accent-light: #1e2a3d;
      --tag-bg: #1e2a3d;
      --tag-text: #93b4f8;
      --chip-active-bg: #2563eb;
      --chip-active-text: #ffffff;
      --shadow: 0 1px 3px rgba(0,0,0,.3);
      --shadow-hover: 0 4px 12px rgba(0,0,0,.4);
      --score-high: #4ade80;
      --score-mid: #fbbf24;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 15px; line-height: 1.55; }}

  /* ── Header ── */
  header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 24px; position: sticky; top: 0; z-index: 100; }}
  .header-inner {{ max-width: 1100px; margin: auto; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  .header-title {{ font-size: 1.15rem; font-weight: 700; color: var(--text); white-space: nowrap; }}
  .header-title span {{ color: var(--accent); }}
  #search {{ flex: 1; min-width: 180px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 14px; outline: none; }}
  #search:focus {{ border-color: var(--accent); }}
  #result-count {{ white-space: nowrap; font-size: 13px; color: var(--muted); }}

  /* ── Filters bar ── */
  .filters {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 10px 24px; position: sticky; top: 61px; z-index: 99; }}
  .filters-inner {{ max-width: 1100px; margin: auto; display: flex; flex-direction: column; gap: 8px; }}
  .filter-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .filter-label {{ font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; min-width: 46px; }}
  .chip {{ display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg); color: var(--muted); font-size: 12.5px; cursor: pointer; user-select: none; transition: background .12s, color .12s, border-color .12s; white-space: nowrap; }}
  .chip:hover {{ border-color: var(--accent); color: var(--accent); }}
  .chip.active {{ background: var(--chip-active-bg); color: var(--chip-active-text); border-color: var(--chip-active-bg); }}
  .chip .count {{ margin-left: 5px; opacity: .75; font-size: 11px; }}

  /* ── Grid ── */
  main {{ max-width: 1100px; margin: 24px auto; padding: 0 24px 48px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}

  /* ── Card ── */
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 10px; transition: box-shadow .15s; }}
  .card:hover {{ box-shadow: var(--shadow-hover); }}
  .card-meta {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .badge {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; }}
  .badge-research {{ background: #e0f2fe; color: #0369a1; }}
  .badge-review {{ background: #fce7f3; color: #9d174d; }}
  .badge-perspective {{ background: #f0fdf4; color: #166534; }}
  @media (prefers-color-scheme: dark) {{
    .badge-research {{ background: #0c2a3d; color: #7dd3fc; }}
    .badge-review {{ background: #3b0a20; color: #f9a8d4; }}
    .badge-perspective {{ background: #052e16; color: #86efac; }}
  }}
  .card-date {{ font-size: 11.5px; color: var(--muted); margin-left: auto; }}
  .score {{ font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 10px; }}
  .score-high {{ background: #dcfce7; color: var(--score-high); }}
  .score-mid {{ background: #fef9c3; color: var(--score-mid); }}
  .score-low {{ background: #f3f4f6; color: var(--score-low); }}
  @media (prefers-color-scheme: dark) {{
    .score-high {{ background: #052e16; }}
    .score-mid {{ background: #2d1a00; }}
    .score-low {{ background: #1f2937; }}
  }}
  .card-title {{ font-size: 15px; font-weight: 650; line-height: 1.4; }}
  .card-title a {{ color: var(--text); text-decoration: none; }}
  .card-title a:hover {{ color: var(--accent); text-decoration: underline; }}
  .card-authors {{ font-size: 13px; color: var(--muted); }}
  .card-venue {{ font-size: 12.5px; color: var(--muted); font-style: italic; }}
  .card-summary {{ font-size: 13.5px; color: var(--text); opacity: .88; }}
  .card-tags {{ display: flex; flex-wrap: wrap; gap: 5px; }}
  .tag {{ font-size: 11.5px; padding: 2px 8px; border-radius: 10px; background: var(--tag-bg); color: var(--tag-text); cursor: pointer; }}
  .tag:hover {{ opacity: .8; }}
  .empty {{ text-align: center; padding: 64px 0; color: var(--muted); font-size: 15px; grid-column: 1/-1; }}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-title">Ru's Reading List <span>· AICS</span></div>
    <input id="search" type="search" placeholder="Search title, author, journal…" autocomplete="off">
    <div id="result-count"></div>
  </div>
</header>

<div class="filters">
  <div class="filters-inner">
    <div class="filter-row" id="type-filters">
      <span class="filter-label">Type</span>
    </div>
    <div class="filter-row" id="tag-filters">
      <span class="filter-label">Topic</span>
    </div>
  </div>
</div>

<main>
  <div class="grid" id="grid"></div>
</main>

<script>
const PAPERS = {papers_json};

// Sort newest-first, then by score
PAPERS.sort((a, b) => {{
  const da = a.added || '', db = b.added || '';
  if (da !== db) return da > db ? -1 : 1;
  return (b.score || 0) - (a.score || 0);
}});

// ── State ──
let activeType = 'all';
let activeTags = new Set();
let searchText = '';

// ── Count helpers ──
function countByType(type) {{
  return type === 'all' ? PAPERS.length : PAPERS.filter(p => (p.type || 'research') === type).length;
}}

// ── Render chips ──
const TYPES = ['all', 'research', 'review', 'perspective'];
const typeRow = document.getElementById('type-filters');
TYPES.forEach(t => {{
  const chip = document.createElement('button');
  chip.className = 'chip' + (t === 'all' ? ' active' : '');
  chip.dataset.type = t;
  const label = t === 'all' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1);
  chip.innerHTML = `${{label}}<span class="count">${{countByType(t)}}</span>`;
  chip.addEventListener('click', () => {{
    activeType = t;
    document.querySelectorAll('#type-filters .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    render();
  }});
  typeRow.appendChild(chip);
}});

// Collect all tags
const tagCounts = {{}};
PAPERS.forEach(p => (p.tags || []).forEach(tag => {{ tagCounts[tag] = (tagCounts[tag] || 0) + 1; }}));
const allTags = Object.entries(tagCounts).sort((a,b) => b[1]-a[1]).map(([t]) => t);

const tagRow = document.getElementById('tag-filters');
allTags.forEach(tag => {{
  const chip = document.createElement('button');
  chip.className = 'chip';
  chip.dataset.tag = tag;
  chip.innerHTML = `${{tag}}<span class="count">${{tagCounts[tag]}}</span>`;
  chip.addEventListener('click', () => {{
    if (activeTags.has(tag)) {{ activeTags.delete(tag); chip.classList.remove('active'); }}
    else {{ activeTags.add(tag); chip.classList.add('active'); }}
    render();
  }});
  tagRow.appendChild(chip);
}});

// ── Search ──
document.getElementById('search').addEventListener('input', e => {{
  searchText = e.target.value.toLowerCase();
  render();
}});

// ── Tag click from card ──
document.getElementById('grid').addEventListener('click', e => {{
  const tag = e.target.dataset.clicktag;
  if (!tag) return;
  if (activeTags.has(tag)) {{ activeTags.delete(tag); }}
  else {{ activeTags.add(tag); }}
  document.querySelectorAll('#tag-filters .chip').forEach(c => {{
    c.classList.toggle('active', activeTags.has(c.dataset.tag));
  }});
  render();
}});

function scoreClass(s) {{
  if (s >= 8) return 'score-high';
  if (s >= 5) return 'score-mid';
  return 'score-low';
}}

function fmt(p) {{
  const type = (p.type || 'research').toLowerCase();
  const badgeClass = 'badge-' + (type === 'research' ? 'research' : type === 'review' ? 'review' : 'perspective');
  const score = typeof p.score === 'number' ? p.score : null;
  const scoreBadge = score !== null ? `<span class="score ${{scoreClass(score)}}">${{score}}/10</span>` : '';
  const titleHtml = p.link
    ? `<a href="${{p.link}}" target="_blank" rel="noopener">${{esc(p.title)}}</a>`
    : esc(p.title);
  const tags = (p.tags || []).map(t =>
    `<span class="tag" data-clicktag="${{esc(t)}}">${{esc(t)}}</span>`
  ).join('');
  const added = p.added ? `<span class="card-date">${{p.added}}</span>` : '';
  const venue = [p.journal, p.year].filter(Boolean).join(' · ');
  return `<div class="card">
    <div class="card-meta">
      <span class="badge ${{badgeClass}}">${{esc(type)}}</span>
      ${{scoreBadge}}
      ${{added}}
    </div>
    <div class="card-title">${{titleHtml}}</div>
    ${{p.authors ? `<div class="card-authors">${{esc(p.authors)}}</div>` : ''}}
    ${{venue ? `<div class="card-venue">${{esc(venue)}}</div>` : ''}}
    ${{p.summary ? `<div class="card-summary">${{esc(p.summary)}}</div>` : ''}}
    ${{tags ? `<div class="card-tags">${{tags}}</div>` : ''}}
  </div>`;
}}

function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function render() {{
  const q = searchText;
  const filtered = PAPERS.filter(p => {{
    if (activeType !== 'all' && (p.type || 'research') !== activeType) return false;
    if (activeTags.size > 0 && !([...(p.tags||[])].some(t => activeTags.has(t)))) return false;
    if (q) {{
      const hay = [p.title, p.authors, p.journal, p.summary, ...(p.tags||[])].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});
  const grid = document.getElementById('grid');
  if (filtered.length === 0) {{
    grid.innerHTML = '<div class="empty">No papers match your filters.</div>';
  }} else {{
    grid.innerHTML = filtered.map(fmt).join('');
  }}
  document.getElementById('result-count').textContent = `${{filtered.length}} paper${{filtered.length === 1 ? '' : 's'}}`;
}}

render();
</script>
</body>
</html>"""


def main():
    if not PAPERS_PATH.exists():
        print("papers.json not found")
        return
    with open(PAPERS_PATH) as f:
        papers = json.load(f)
    html = build_html(papers)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH} ({len(papers)} papers)")


if __name__ == "__main__":
    main()
