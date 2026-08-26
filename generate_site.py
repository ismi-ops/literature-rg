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
<title>Ru's Reading List · Cell Science</title>
<style>
  :root {
    --bg: #F3F0E8; --surface: #ffffff; --border: #DED9D1;
    --text: #1a1d23; --muted: #737373; --accent: #6464FF;
    --accent-light: #efecff; --tag-bg: #edeaff; --tag-text: #6464FF;
    --chip-active-bg: #6464FF; --chip-active-text: #ffffff;
    --shadow: 0 1px 3px rgba(0,0,0,.08); --shadow-hover: 0 4px 12px rgba(0,0,0,.12);
    --radius: 10px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1117; --surface: #1c1f27; --border: #2a2e38;
      --text: #e8eaf0; --muted: #AAA39F; --accent: #8b8bff;
      --accent-light: #1a1a3d; --tag-bg: #1a1a3d; --tag-text: #a0a0ff;
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
  .card { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 10px; transition: box-shadow .15s; }
  .card:hover { box-shadow: var(--shadow-hover); }
  .top-pick-star { position: absolute; bottom: 12px; right: 14px; font-size: 20px; line-height: 1; user-select: none; cursor: default; filter: drop-shadow(0 1px 2px rgba(0,0,0,.15)); }
  .card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; }
  .badge-research { background: #edeaff; color: #6464FF; }
  .badge-review { background: #fde8f0; color: #CD0F55; }
  .badge-perspective { background: #e0faf9; color: #007d75; }
  @media (prefers-color-scheme: dark) {
    .badge-research { background: #1a1a3d; color: #a0a0ff; }
    .badge-review { background: #3b0018; color: #ff80aa; }
    .badge-perspective { background: #003630; color: #4dd9d3; }
    .card-relevance { border-color: #00A59B; background: transparent; }
    .card-relevance-label { color: #4dd9d3; }
    .card-relevance-text { color: #4dd9d3; opacity: .85; }
    .tag { background: transparent; color: #a0a0ff; border-color: #a0a0ff; }
    .btn-pdf { background: transparent; color: #ff80aa; border-color: #ff80aa; }
  }
  .card-date { font-size: 11.5px; color: var(--muted); margin-left: auto; }
  .card-title { font-size: 15px; font-weight: 650; line-height: 1.4; }
  .card-title a { color: var(--text); text-decoration: none; }
  .card-title a:hover { color: var(--accent); text-decoration: underline; }
  .card-authors { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px 6px; }
  .author-link { color: var(--muted); text-decoration: none; }
  .author-link:hover { color: var(--accent); text-decoration: underline; }
  .card-venue { font-size: 12.5px; color: var(--muted); font-style: italic; }
  .journal-link { color: inherit; text-decoration: none; }
  .journal-link:hover { text-decoration: underline; }
  .card-summary { font-size: 13.5px; color: var(--text); opacity: .88; }
  .card-relevance { margin-top: 10px; border-left: 3px solid #00A59B; border-radius: 4px; background: transparent; padding: 8px 12px; }
  .card-relevance-label { font-size: 10.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #007d75; opacity: .9; margin-bottom: 3px; }
  .card-relevance-text { font-size: 13px; color: #005c57; font-style: italic; line-height: 1.45; }
  .card-tags { display: flex; flex-wrap: wrap; gap: 5px; }
  .tag { font-size: 11.5px; padding: 2px 8px; border-radius: 10px; background: transparent; color: #6464FF; border: 1px solid #6464FF; cursor: pointer; }
  .tag:hover { opacity: .8; }
  .card-actions { display: flex; gap: 8px; margin-top: 2px; align-items: center; }
  .btn-pdf { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 7px; background: transparent; color: #CD0F55; text-decoration: none; border: 1px solid #CD0F55; opacity: .85; transition: opacity .12s; }
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

  /* ── Add Paper modal ──────────────────────────────────────────────────── */
  .modal-backdrop { display: none; position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,.45); align-items: center; justify-content: center; }
  .modal-backdrop.open { display: flex; }
  .modal-box { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 32px 28px; width: 440px; max-width: 94vw; box-shadow: 0 8px 32px rgba(0,0,0,.22); display: flex; flex-direction: column; gap: 14px; }
  .modal-header { display: flex; align-items: center; justify-content: space-between; }
  .modal-title { font-size: 1.05rem; font-weight: 700; }
  .modal-close { background: none; border: none; font-size: 22px; cursor: pointer; color: var(--muted); line-height: 1; padding: 0 4px; transition: color .12s; }
  .modal-close:hover { color: var(--text); }
  .modal-label { font-size: 13px; font-weight: 600; }
  .modal-desc { font-size: 13px; color: var(--muted); line-height: 1.5; }
  .modal-input { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 14px; outline: none; }
  .modal-input:focus { border-color: var(--accent); }
  .modal-btn { width: 100%; padding: 10px; border-radius: 8px; border: none; background: var(--accent); color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity .12s; }
  .modal-btn:hover { opacity: .88; }
  .modal-btn:disabled { opacity: .5; cursor: default; }
  .modal-feedback { font-size: 13px; min-height: 18px; }
  .modal-feedback.ok { color: #16a34a; }
  .modal-feedback.err { color: #dc2626; }
  .modal-link { color: var(--accent); }
  .modal-token-row { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
  .modal-token-btn { background: none; border: none; color: var(--accent); font-size: 12px; cursor: pointer; padding: 0; text-decoration: underline; }
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
    <div class="header-title">Ru's Reading List <span>· Cell Science</span></div>
    <input id="search" type="search" placeholder="Search title, author, journal…" autocomplete="off">
    <div id="result-count"></div>
    <button class="btn-add" id="btn-add-paper">+ Add paper</button>
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

<!-- Add Paper modal -->
<div class="modal-backdrop" id="add-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title-text">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title" id="modal-title-text">Add Paper</span>
      <button class="modal-close" id="modal-close" aria-label="Close">&times;</button>
    </div>

    <!-- Screen 1: GitHub token setup -->
    <div id="modal-token-screen">
      <p class="modal-desc">To add papers you need a GitHub Personal Access Token (PAT) with the <strong>workflow</strong> scope. It's stored only in your browser.</p>
      <p class="modal-desc"><a class="modal-link" href="https://github.com/settings/tokens/new?scopes=workflow&description=literature-rg" target="_blank" rel="noopener">Create a token on GitHub →</a></p>
      <div class="modal-label">Personal Access Token</div>
      <input class="modal-input" id="token-input" type="password" placeholder="ghp_…" autocomplete="off">
      <button class="modal-btn" id="token-save-btn">Save &amp; continue</button>
      <div class="modal-feedback" id="token-feedback"></div>
    </div>

    <!-- Screen 2: Paper URL / DOI input -->
    <div id="modal-paper-screen" style="display:none">
      <div class="modal-label">Paper URL or DOI</div>
      <p class="modal-desc">Paste a link (Nature, bioRxiv, PubMed…) or a DOI like <code>10.1038/…</code>. The paper will be scored and added automatically — check back in ~2 minutes.</p>
      <input class="modal-input" id="paper-input" type="text" placeholder="https://… or 10.xxxx/…" autocomplete="off">
      <button class="modal-btn" id="paper-submit-btn">+ Add paper</button>
      <div class="modal-feedback" id="paper-feedback"></div>
      <div class="modal-token-row">Token saved. <button class="modal-token-btn" id="change-token-btn">Change token</button></div>
    </div>
  </div>
</div>

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

/* ── Top picks (highest-scored 4 from the past 7 days) ──────────────────── */
const _latestDate = PAPERS.reduce((max, p) => (p.added||'') > max ? (p.added||'') : max, '');
const _sevenDaysAgo = (() => { const d = new Date(_latestDate || new Date()); d.setDate(d.getDate()-7); return d.toISOString().slice(0,10); })();
const _recentBatch = PAPERS.filter(p => (p.added||'') >= _sevenDaysAgo)
  .slice().sort((a, b) => (b.score||0) - (a.score||0));
const TOP_PICK_IDS = new Set(_recentBatch.slice(0, 4).map(p => p.doi || p.title || ''));
function isTopPick(p) { return TOP_PICK_IDS.size > 0 && TOP_PICK_IDS.has(p.doi || p.title || ''); }

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

/* ── Journal URL map ────────────────────────────────────────────────────── */
const JOURNAL_URLS = {
  'nature': 'https://www.nature.com/nature/',
  'science': 'https://www.science.org/journal/science',
  'cell': 'https://www.cell.com/cell/home',
  'nature cell biology': 'https://www.nature.com/ncb/',
  'nature methods': 'https://www.nature.com/nmeth/',
  'nature communications': 'https://www.nature.com/ncomms/',
  'nature biotechnology': 'https://www.nature.com/nbt/',
  'nature reviews molecular cell biology': 'https://www.nature.com/nrm/',
  'nature reviews genetics': 'https://www.nature.com/nrg/',
  'nature reviews bioengineering': 'https://www.nature.com/natrevbioeng/',
  'nature chemical biology': 'https://www.nature.com/nchembio/',
  'nature computational science': 'https://www.nature.com/natcomputsci/',
  'nature nanotechnology': 'https://www.nature.com/nnano/',
  'developmental cell': 'https://www.cell.com/developmental-cell/home',
  'cell stem cell': 'https://www.cell.com/cell-stem-cell/home',
  'cell reports': 'https://www.cell.com/cell-reports/home',
  'cell reports methods': 'https://www.cell.com/cell-reports-methods/home',
  'cell systems': 'https://www.cell.com/cell-systems/home',
  'molecular biology of the cell': 'https://www.molbiolcell.org/',
  'molecular biology of the cell (mboc)': 'https://www.molbiolcell.org/',
  'elife': 'https://elifesciences.org/',
  'development': 'https://journals.biologists.com/dev',
  'development (cambridge, england)': 'https://journals.biologists.com/dev',
  'developmental biology': 'https://www.sciencedirect.com/journal/developmental-biology',
  'biophysical journal': 'https://www.cell.com/biophysical-journal/home',
  'plos computational biology': 'https://journals.plos.org/ploscompbiol/',
  'annual review of cell and developmental biology': 'https://www.annualreviews.org/journal/cellbio',
  'annual review of biomedical data science': 'https://www.annualreviews.org/journal/biodatasci',
  'journal of cell biology': 'https://www.jcb.org/',
  'stem cell reports': 'https://www.cell.com/stem-cell-reports/home',
  'stem cells': 'https://stemcellsjournals.onlinelibrary.wiley.com/journal/15494918',
  'frontiers in bioengineering and biotechnology': 'https://www.frontiersin.org/journals/bioengineering-and-biotechnology',
  'frontiers in cell and developmental biology': 'https://www.frontiersin.org/journals/cell-and-developmental-biology',
  'npj systems biology and applications': 'https://www.nature.com/npjsba/',
  'seminars in cell & developmental biology': 'https://www.sciencedirect.com/journal/seminars-in-cell-and-developmental-biology',
  'seminars in cell and developmental biology': 'https://www.sciencedirect.com/journal/seminars-in-cell-and-developmental-biology',
  'current opinion in genetics and development': 'https://www.sciencedirect.com/journal/current-opinion-in-genetics-and-development',
  'advanced science': 'https://onlinelibrary.wiley.com/journal/21983844',
  'biorxiv': 'https://www.biorxiv.org/',
  'arxiv': 'https://arxiv.org/',
};
function journalUrl(name) {
  if (!name) return '';
  return JOURNAL_URLS[name.toLowerCase().trim()] || '';
}

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
  const jUrl = journalUrl(p.journal);
  const journalHtml = p.journal ? (jUrl ? '<a class="journal-link" href="'+esc(jUrl)+'" target="_blank" rel="noopener">'+esc(p.journal)+'</a>' : esc(p.journal)) : '';
  const venue = [journalHtml, p.year ? esc(p.year) : ''].filter(Boolean).join(' · ');
  const pdfBtn = p.pdf_link ? '<a class="btn-pdf" href="'+esc(p.pdf_link)+'" target="_blank" rel="noopener">&#8595; PDF</a>' : '';
  const existingNote = getNote(p);
  const hasNote = existingNote.trim().length > 0;
  const noteId = 'note-' + Math.random().toString(36).slice(2);
  const starHtml = isTopPick(p) ? '<div class="top-pick-star" title="Top pick · recommended for printing">⭐</div>' : '';
  return '<div class="card">'
    +'<div class="card-meta"><span class="badge '+badgeClass+'">'+esc(type)+'</span>'+added+'</div>'
    +'<div class="card-title">'+titleHtml+'</div>'
    +(authorHtml ? '<div class="card-authors">'+authorHtml+'</div>' : '')
    +(venue ? '<div class="card-venue">'+venue+'</div>' : '')
    +(p.summary ? '<div class="card-summary">'+esc(p.summary)+'</div>' : '')
    +(p.relevance ? '<div class="card-relevance"><div class="card-relevance-label">Cell Science relevance</div><div class="card-relevance-text">'+esc(p.relevance)+'</div></div>' : '')
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
    +starHtml
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

/* ── Add Paper modal ────────────────────────────────────────────────────── */
const GH_TOKEN_KEY = 'rg_gh_token';
const addModal = document.getElementById('add-modal');
const tokenScreen = document.getElementById('modal-token-screen');
const paperScreen = document.getElementById('modal-paper-screen');

function getToken() { try { return localStorage.getItem(GH_TOKEN_KEY) || ''; } catch(e) { return ''; } }
function saveToken(t) { try { localStorage.setItem(GH_TOKEN_KEY, t); return true; } catch(e) { return false; } }

function showTokenScreen() {
  tokenScreen.style.display = '';
  paperScreen.style.display = 'none';
  document.getElementById('token-input').value = '';
  document.getElementById('token-feedback').textContent = '';
  document.getElementById('token-feedback').className = 'modal-feedback';
  setTimeout(() => document.getElementById('token-input').focus(), 60);
}
function showPaperScreen() {
  tokenScreen.style.display = 'none';
  paperScreen.style.display = '';
  document.getElementById('paper-input').value = '';
  document.getElementById('paper-feedback').textContent = '';
  document.getElementById('paper-feedback').className = 'modal-feedback';
  setTimeout(() => document.getElementById('paper-input').focus(), 60);
}

function openAddModal() {
  addModal.classList.add('open');
  getToken() ? showPaperScreen() : showTokenScreen();
}
function closeAddModal() { addModal.classList.remove('open'); }

document.getElementById('btn-add-paper').addEventListener('click', openAddModal);
document.getElementById('modal-close').addEventListener('click', closeAddModal);
addModal.addEventListener('click', e => { if (e.target === addModal) closeAddModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && addModal.classList.contains('open')) closeAddModal(); });

document.getElementById('token-save-btn').addEventListener('click', () => {
  const val = document.getElementById('token-input').value.trim();
  const fb = document.getElementById('token-feedback');
  if (!val) { fb.className = 'modal-feedback err'; fb.textContent = 'Please enter a token.'; return; }
  if (!saveToken(val)) { fb.className = 'modal-feedback err'; fb.textContent = 'Could not save token (browser storage may be blocked).'; return; }
  showPaperScreen();
});
document.getElementById('token-input').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('token-save-btn').click(); });

document.getElementById('change-token-btn').addEventListener('click', showTokenScreen);

document.getElementById('paper-submit-btn').addEventListener('click', async () => {
  const raw = document.getElementById('paper-input').value.trim();
  const fb = document.getElementById('paper-feedback');
  const btn = document.getElementById('paper-submit-btn');
  if (!raw) { fb.className = 'modal-feedback err'; fb.textContent = 'Please enter a URL or DOI.'; return; }

  const token = getToken();
  if (!token) { showTokenScreen(); return; }

  const isDOI = /^10\.\d{4,}\//.test(raw);
  const inputs = isDOI ? { doi: raw, url: '' } : { url: raw, doi: '' };

  btn.disabled = true;
  fb.className = 'modal-feedback';
  fb.textContent = 'Submitting…';

  try {
    const resp = await fetch(
      'https://api.github.com/repos/ismi-ops/literature-rg/actions/workflows/add_paper.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Accept': 'application/vnd.github+json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main', inputs }),
      }
    );
    if (resp.status === 204) {
      fb.className = 'modal-feedback ok';
      fb.textContent = '✓ Submitted! The paper will appear in ~2 minutes after the workflow finishes.';
      document.getElementById('paper-input').value = '';
    } else if (resp.status === 401) {
      fb.className = 'modal-feedback err';
      fb.textContent = 'Invalid token (401). Please update your GitHub PAT.';
    } else if (resp.status === 403) {
      fb.className = 'modal-feedback err';
      fb.textContent = 'Permission denied (403). Make sure the token has "workflow" scope.';
    } else if (resp.status === 422) {
      fb.className = 'modal-feedback err';
      fb.textContent = 'Workflow not found (422). Check that the branch "main" exists.';
    } else {
      const body = await resp.text().catch(() => '');
      fb.className = 'modal-feedback err';
      fb.textContent = 'GitHub error ' + resp.status + (body ? ': ' + body.slice(0, 120) : '');
    }
  } catch(err) {
    fb.className = 'modal-feedback err';
    fb.textContent = 'Network error: ' + err.message;
  }
  btn.disabled = false;
});
document.getElementById('paper-input').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('paper-submit-btn').click(); });
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
