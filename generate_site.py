"""Generate index.html from papers.json."""
import json
from pathlib import Path

PAPERS_PATH = Path("papers.json")
OUTPUT_PATH = Path("index.html")


def build_html(papers):
    papers_json = json.dumps(papers, ensure_ascii=False)
    return HTML_TEMPLATE.replace("__PAPERS_JSON__", papers_json)


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ru's Reading List · AICS</title>
<style>
  :root {
    --bg: #f8f9fb; --surface: #ffffff; --border: #e2e5ea;
    --text: #1a1d23; --muted: #6b7280; --accent: #2563eb;
    --accent-light: #eff6ff; --tag-bg: #f0f4ff; --tag-text: #3b4fc0;
    --chip-active-bg: #2563eb; --chip-active-text: #ffffff;
    --shadow: 0 1px 3px rgba(0,0,0,.08); --shadow-hover: 0 4px 12px rgba(0,0,0,.12);
    --radius: 10px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1117; --surface: #1c1f27; --border: #2a2e38;
      --text: #e8eaf0; --muted: #9ca3af; --accent: #60a5fa;
      --accent-light: #1e2a3d; --tag-bg: #1e2a3d; --tag-text: #93b4f8;
      --shadow: 0 1px 3px rgba(0,0,0,.3); --shadow-hover: 0 4px 12px rgba(0,0,0,.4);
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 15px; line-height: 1.55; }

  /* ── Password overlay ─────────────────────────────────────────────────── */
  #pw-overlay {
    position: fixed; inset: 0; z-index: 9999;
    background: var(--bg);
    display: flex; align-items: center; justify-content: center;
  }
  #pw-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 40px 36px; width: 340px; max-width: 90vw;
    box-shadow: 0 8px 32px rgba(0,0,0,.12);
    display: flex; flex-direction: column; gap: 18px; text-align: center;
  }
  #pw-box h2 { font-size: 1.1rem; font-weight: 700; }
  #pw-box p  { font-size: 13px; color: var(--muted); }
  #pw-input {
    width: 100%; padding: 10px 14px; border: 1px solid var(--border);
    border-radius: 8px; background: var(--bg); color: var(--text);
    font-size: 15px; outline: none; text-align: center; letter-spacing: .05em;
  }
  #pw-input:focus { border-color: var(--accent); }
  #pw-btn {
    width: 100%; padding: 10px; border-radius: 8px; border: none;
    background: var(--accent); color: #fff; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: opacity .12s;
  }
  #pw-btn:hover { opacity: .88; }
  #pw-error { font-size: 13px; color: #dc2626; min-height: 18px; }

  /* ── Header & filters ─────────────────────────────────────────────────── */
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 24px; position: sticky; top: 0; z-index: 100; }
  .header-inner { max-width: 1100px; margin: auto; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .header-title { font-size: 1.15rem; font-weight: 700; color: var(--text); white-space: nowrap; }
  .header-title span { color: var(--accent); }
  #search { flex: 1; min-width: 180px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 14px; outline: none; }
  #search:focus { border-color: var(--accent); }
  #result-count { white-space: nowrap; font-size: 13px; color: var(--muted); }
  .filters { background: var(--surface); border-bottom: 1px solid var(--border); padding: 10px 24px; position: sticky; top: 61px; z-index: 99; }
  .filters-inner { max-width: 1100px; margin: auto; display: flex; flex-direction: column; gap: 8px; }
  .filter-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .filter-label { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; min-width: 52px; }
  .chip { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg); color: var(--muted); font-size: 12.5px; cursor: pointer; user-select: none; transition: background .12s, color .12s, border-color .12s; white-space: nowrap; }
  .chip:hover { border-color: var(--accent); color: var(--accent); }
  .chip.active { background: var(--chip-active-bg); color: var(--chip-active-text); border-color: var(--chip-active-bg); }
  .chip .count { margin-left: 5px; opacity: .75; font-size: 11px; }

  /* ── Cards ────────────────────────────────────────────────────────────── */
  main { max-width: 1100px; margin: 24px auto; padding: 0 24px 48px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 10px; transition: box-shadow .15s; }
  .card:hover { box-shadow: var(--shadow-hover); }
  .card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; }
  .badge-research { background: #e0f2fe; color: #0369a1; }
  .badge-review { background: #fce7f3; color: #9d174d; }
  .badge-perspective { background: #f0fdf4; color: #166534; }
  @media (prefers-color-scheme: dark) {
    .badge-research { background: #0c2a3d; color: #7dd3fc; }
    .badge-review { background: #3b0a20; color: #f9a8d4; }
    .badge-perspective { background: #052e16; color: #86efac; }
  }
  .card-date { font-size: 11.5px; color: var(--muted); margin-left: auto; }
  .card-title { font-size: 15px; font-weight: 650; line-height: 1.4; }
  .card-title a { color: var(--text); text-decoration: none; }
  .card-title a:hover { color: var(--accent); text-decoration: underline; }
  .card-authors { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px 6px; }
  .author-link { color: var(--muted); text-decoration: none; }
  .author-link:hover { color: var(--accent); text-decoration: underline; }
  .card-venue { font-size: 12.5px; color: var(--muted); font-style: italic; }
  .card-summary { font-size: 13.5px; color: var(--text); opacity: .88; }
  .card-tags { display: flex; flex-wrap: wrap; gap: 5px; }
  .tag { font-size: 11.5px; padding: 2px 8px; border-radius: 10px; background: var(--tag-bg); color: var(--tag-text); cursor: pointer; }
  .tag:hover { opacity: .8; }
  .card-actions { display: flex; gap: 8px; margin-top: 2px; align-items: center; }
  .btn-pdf { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 7px; background: var(--accent-light); color: var(--accent); text-decoration: none; border: 1px solid currentColor; opacity: .85; transition: opacity .12s; }
  .btn-pdf:hover { opacity: 1; }
  .notes-section { margin-top: 6px; }
  .notes-toggle { background: none; border: none; padding: 0; font-size: 12px; color: var(--muted); cursor: pointer; display: flex; align-items: center; gap: 4px; transition: color .12s; }
  .notes-toggle:hover { color: var(--accent); }
  .notes-toggle.has-notes { color: var(--accent); font-weight: 600; }
  .notes-area { display: none; margin-top: 6px; }
  .notes-area.open { display: block; }
  .notes-textarea { width: 100%; min-height: 72px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 7px; background: var(--bg); color: var(--text); font-size: 13px; font-family: inherit; line-height: 1.5; resize: vertical; outline: none; transition: border-color .12s; }
  .notes-textarea:focus { border-color: var(--accent); }
  .notes-saved { font-size: 11px; color: var(--muted); margin-top: 3px; min-height: 14px; }
  .empty { text-align: center; padding: 64px 0; color: var(--muted); font-size: 15px; grid-column: 1/-1; }
  .btn-add { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; padding: 7px 14px; border-radius: 8px; background: var(--accent); color: #fff; text-decoration: none; border: none; cursor: pointer; transition: opacity .12s; white-space: nowrap; }
  .btn-add:hover { opacity: .85; }
  .card-notes { margin-top: 4px; }
  .notes-textarea { width: 100%; min-height: 52px; padding: 7px 10px; border: 1px dashed var(--border); border-radius: 7px; background: transparent; color: var(--text); font-size: 12.5px; font-family: inherit; line-height: 1.5; resize: vertical; outline: none; transition: border-color .15s, background .15s; }
  .notes-textarea::placeholder { color: var(--muted); opacity: .7; font-style: italic; }
  .notes-textarea:focus { border-color: var(--accent); border-style: solid; background: var(--accent-light); }
</style>
</head>
<body>

<!-- Password overlay -->
<div id="pw-overlay">
  <div id="pw-box">
    <h2>Ru's Reading List</h2>
    <p>Enter the password to continue.</p>
    <input id="pw-input" type="password" placeholder="Password" autocomplete="current-password">
    <div id="pw-error"></div>
    <button id="pw-btn">Unlock</button>
  </div>
</div>

<header>
  <div class="header-inner">
    <div class="header-title">Ru's Reading List <span>· AICS</span></div>
    <input id="search" type="search" placeholder="Search title, author, journal…" autocomplete="off">
    <div id="result-count"></div>
    <a class="btn-add" href="https://github.com/ismi-ops/literature-rg/actions/workflows/add_paper.yml" target="_blank" rel="noopener">+ Add paper</a>
  </div>
</header>
<div class="filters">
  <div class="filters-inner">
    <div class="filter-row" id="type-filters"><span class="filter-label">Type</span></div>
    <div class="filter-row" id="tag-filters"><span class="filter-label">Topic</span></div>
    <div class="filter-row" id="year-filters"><span class="filter-label">Year</span></div>
    <div class="filter-row" id="added-filters"><span class="filter-label">Added</span></div>
  </div>
</div>
<main><div class="grid" id="grid"></div></main>

<script>
/* ── Password gate ──────────────────────────────────────────────────────── */
const PW_KEY = 'rg_unlocked';
const CORRECT_PW = 'RG-literature';
const overlay = document.getElementById('pw-overlay');
function unlock() {
  overlay.style.display = 'none';
  localStorage.setItem(PW_KEY, '1');
}
if (localStorage.getItem(PW_KEY) === '1') { unlock(); }
document.getElementById('pw-btn').addEventListener('click', () => {
  if (document.getElementById('pw-input').value === CORRECT_PW) {
    unlock();
  } else {
    document.getElementById('pw-error').textContent = 'Incorrect password.';
  }
});
document.getElementById('pw-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('pw-btn').click();
  document.getElementById('pw-error').textContent = '';
});

/* ── Data ───────────────────────────────────────────────────────────────── */
const PAPERS = __PAPERS_JSON__;
PAPERS.sort((a, b) => {
  const da = a.added || '', db = b.added || '';
  if (da !== db) return da > db ? -1 : 1;
  return (b.score || 0) - (a.score || 0);
});

/* ── Filter state ───────────────────────────────────────────────────────── */
let activeType = 'all', activeTags = new Set(), activeYear = 'all', activeAdded = 'all', searchText = '';

/* ── Type chips ─────────────────────────────────────────────────────────── */
function countByType(type) {
  return type === 'all' ? PAPERS.length : PAPERS.filter(p => (p.type||'research') === type).length;
}
const TYPES = ['all','research','review','perspective'];
const typeRow = document.getElementById('type-filters');
TYPES.forEach(t => {
  const chip = document.createElement('button');
  chip.className = 'chip' + (t === 'all' ? ' active' : '');
  chip.dataset.type = t;
  const label = t === 'all' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1);
  chip.innerHTML = label + '<span class="count">' + countByType(t) + '</span>';
  chip.addEventListener('click', () => {
    activeType = t;
    document.querySelectorAll('#type-filters .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active'); render();
  });
  typeRow.appendChild(chip);
});

/* ── Topic tag chips ────────────────────────────────────────────────────── */
const TAG_BLOCKLIST = new Set(['perspective','perspectives','review','research','preprint','editorial','comment','letter']);
function isTopicTag(t) { return !TAG_BLOCKLIST.has(t.toLowerCase()); }
const tagCounts = {};
PAPERS.forEach(p => (p.tags||[]).filter(isTopicTag).forEach(tag => { tagCounts[tag] = (tagCounts[tag]||0)+1; }));
const allTags = Object.entries(tagCounts).sort((a,b)=>b[1]-a[1]).map(([t])=>t);
const tagRow = document.getElementById('tag-filters');
allTags.forEach(tag => {
  const chip = document.createElement('button');
  chip.className = 'chip'; chip.dataset.tag = tag;
  chip.innerHTML = tag + '<span class="count">' + tagCounts[tag] + '</span>';
  chip.addEventListener('click', () => {
    if (activeTags.has(tag)) { activeTags.delete(tag); chip.classList.remove('active'); }
    else { activeTags.add(tag); chip.classList.add('active'); }
    render();
  });
  tagRow.appendChild(chip);
});

/* ── Publication year chips ─────────────────────────────────────────────── */
const yearCounts = {};
PAPERS.forEach(p => { const y = String(p.year||'').trim(); if (y) yearCounts[y] = (yearCounts[y]||0)+1; });
const allYears = Object.keys(yearCounts).sort((a,b)=>b-a);
const yearRow = document.getElementById('year-filters');
{
  const chip = document.createElement('button');
  chip.className = 'chip active'; chip.dataset.year = 'all';
  chip.innerHTML = 'All<span class="count">'+PAPERS.length+'</span>';
  chip.addEventListener('click', () => {
    activeYear = 'all';
    document.querySelectorAll('#year-filters .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active'); render();
  });
  yearRow.appendChild(chip);
}
allYears.forEach(y => {
  const chip = document.createElement('button');
  chip.className = 'chip'; chip.dataset.year = y;
  chip.innerHTML = y + '<span class="count">'+yearCounts[y]+'</span>';
  chip.addEventListener('click', () => {
    activeYear = y;
    document.querySelectorAll('#year-filters .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active'); render();
  });
  yearRow.appendChild(chip);
});

/* ── Date-added chips ───────────────────────────────────────────────────── */
const today = new Date();
function daysAgo(n) {
  const d = new Date(today); d.setDate(d.getDate()-n); return d.toISOString().slice(0,10);
}
const ADDED_RANGES = [
  { label: 'All', key: 'all' },
  { label: 'Last 30 days', key: '30' },
  { label: 'Last 3 months', key: '90' },
  { label: 'Last 6 months', key: '180' },
  { label: 'This year', key: 'year' },
];
function addedCount(key) {
  if (key === 'all') return PAPERS.length;
  const cutoff = key === 'year' ? String(today.getFullYear())+'-01-01' : daysAgo(parseInt(key));
  return PAPERS.filter(p => (p.added||'') >= cutoff).length;
}
const addedRow = document.getElementById('added-filters');
ADDED_RANGES.forEach(({label, key}) => {
  const chip = document.createElement('button');
  chip.className = 'chip' + (key === 'all' ? ' active' : ''); chip.dataset.added = key;
  chip.innerHTML = label + '<span class="count">'+addedCount(key)+'</span>';
  chip.addEventListener('click', () => {
    activeAdded = key;
    document.querySelectorAll('#added-filters .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active'); render();
  });
  addedRow.appendChild(chip);
});

/* ── Search ─────────────────────────────────────────────────────────────── */
document.getElementById('search').addEventListener('input', e => { searchText = e.target.value.toLowerCase(); render(); });

/* ── Tag clicks inside grid ─────────────────────────────────────────────── */
document.getElementById('grid').addEventListener('click', e => {
  const tag = e.target.dataset.clicktag;
  if (!tag) return;
  if (activeTags.has(tag)) activeTags.delete(tag); else activeTags.add(tag);
  document.querySelectorAll('#tag-filters .chip').forEach(c => { c.classList.toggle('active', activeTags.has(c.dataset.tag)); });
  render();
});

/* ── Notes storage (localStorage) ───────────────────────────────────────── */
function noteKey(p) { return 'note:' + (p.doi || p.title || '').slice(0, 120); }
function getNote(p) { try { return localStorage.getItem(noteKey(p)) || ''; } catch(e) { return ''; } }
function setNote(p, v) { try { localStorage.setItem(noteKey(p), v); } catch(e) {} }

/* ── Card rendering ─────────────────────────────────────────────────────── */
function authorLink(name) { return 'https://scholar.google.com/scholar?q=' + encodeURIComponent(name); }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(p) {
  const type = (p.type||'research').toLowerCase();
  const badgeClass = 'badge-'+(type==='review'?'review':type==='perspective'?'perspective':'research');
  const titleHtml = p.link ? '<a href="'+esc(p.link)+'" target="_blank" rel="noopener">'+esc(p.title)+'</a>' : esc(p.title);
  const rawAuthors = typeof p.authors === 'string' ? p.authors : (p.authors||[]).join(', ');
  const authorNames = rawAuthors.split(/,\s*et al\.?/).map(s=>s.trim()).join('').split(/,\s*/).map(s=>s.trim()).filter(Boolean);
  const authorHtml = authorNames.map(a => {
    const name = a.replace(/\s*et al\.?\s*$/,'').trim();
    return name ? '<a class="author-link" href="'+authorLink(name)+'" target="_blank" rel="noopener">'+esc(name)+'</a>' : '';
  }).filter(Boolean).join('<span style="color:var(--border)"> · </span>');
  const tags = (p.tags||[]).filter(isTopicTag).map(t=>'<span class="tag" data-clicktag="'+esc(t)+'">'+esc(t)+'</span>').join('');
  const added = p.added ? '<span class="card-date">added '+p.added+'</span>' : '';
  const venue = [p.journal, p.year].filter(Boolean).join(' · ');
  const pdfBtn = p.pdf_link ? '<a class="btn-pdf" href="'+esc(p.pdf_link)+'" target="_blank" rel="noopener">&#8595; PDF</a>' : '';
  const existingNote = getNote(p);
  const hasNote = existingNote.trim().length > 0;
  const noteId = 'note-' + Math.random().toString(36).slice(2);
  return '<div class="card">'
    +'<div class="card-meta"><span class="badge '+badgeClass+'">'+esc(type)+'</span>'+added+'</div>'
    +'<div class="card-title">'+titleHtml+'</div>'
    +(authorHtml ? '<div class="card-authors">'+authorHtml+'</div>' : '')
    +(venue ? '<div class="card-venue">'+esc(venue)+'</div>' : '')
    +(p.summary ? '<div class="card-summary">'+esc(p.summary)+'</div>' : '')
    +(tags ? '<div class="card-tags">'+tags+'</div>' : '')
    +(pdfBtn ? '<div class="card-actions">'+pdfBtn+'</div>' : '')
    +'<div class="notes-section">'
      +'<button class="notes-toggle'+(hasNote?' has-notes':'')+'" data-noteid="'+noteId+'">'
        +(hasNote ? '&#128221; Notes' : '+ Add note')
      +'</button>'
      +'<div class="notes-area" id="'+noteId+'">'
        +'<textarea class="notes-textarea" rows="3" placeholder="Your notes…">'+esc(existingNote)+'</textarea>'
        +'<div class="notes-saved"></div>'
      +'</div>'
    +'</div>'
    +'</div>';
}

/* ── Notes interaction ──────────────────────────────────────────────────── */
let _papersByNoteId = {};
function bindNotes(paper, noteId) {
  _papersByNoteId[noteId] = paper;
}
document.getElementById('grid').addEventListener('click', e => {
  const btn = e.target.closest('.notes-toggle');
  if (!btn) return;
  const id = btn.dataset.noteid;
  const area = document.getElementById(id);
  if (!area) return;
  area.classList.toggle('open');
  if (area.classList.contains('open')) {
    area.querySelector('textarea').focus();
  }
});
document.getElementById('grid').addEventListener('input', e => {
  if (!e.target.classList.contains('notes-textarea')) return;
  const area = e.target.closest('.notes-area');
  const noteId = area?.id;
  const paper = _papersByNoteId[noteId];
  if (!paper) return;
  setNote(paper, e.target.value);
  const saved = area.querySelector('.notes-saved');
  if (saved) saved.textContent = 'Saved';
  const toggle = document.querySelector('[data-noteid="'+noteId+'"]');
  if (toggle) {
    const hasNote = e.target.value.trim().length > 0;
    toggle.classList.toggle('has-notes', hasNote);
    toggle.textContent = hasNote ? '📑 Notes' : '+ Add note';
    toggle.dataset.noteid = noteId;
  }
});

/* ── Render ─────────────────────────────────────────────────────────────── */
function render() {
  const q = searchText;
  const addedCutoff = activeAdded === 'all' ? '' : activeAdded === 'year' ? String(today.getFullYear())+'-01-01' : daysAgo(parseInt(activeAdded));
  const filtered = PAPERS.filter(p => {
    if (activeType !== 'all' && (p.type||'research') !== activeType) return false;
    if (activeTags.size > 0 && ![...(p.tags||[])].some(t => activeTags.has(t))) return false;
    if (activeYear !== 'all' && String(p.year||'').trim() !== activeYear) return false;
    if (addedCutoff && (p.added||'') < addedCutoff) return false;
    if (q) { const hay = [p.title, p.authors, p.journal, p.summary,...(p.tags||[])].join(' ').toLowerCase(); if (!hay.includes(q)) return false; }
    return true;
  });
  _papersByNoteId = {};
  const grid = document.getElementById('grid');
  if (filtered.length) {
    const cards = filtered.map(p => {
      const html = fmt(p);
      // extract the noteId we just generated so we can register it
      const m = html.match(/data-noteid="(note-[^"]+)"/);
      if (m) _papersByNoteId[m[1]] = p;
      return html;
    });
    grid.innerHTML = cards.join('');
  } else {
    grid.innerHTML = '<div class="empty">No papers match your filters.</div>';
  }
  document.getElementById('result-count').textContent = filtered.length+' paper'+(filtered.length===1?'':'s');
}
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
