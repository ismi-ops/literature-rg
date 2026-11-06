/* app.js — Ru's Reading List.
   Boot order: index.html shell (+ inline password gate) -> this script -> filters.json (builds the
   filter UI) -> papers_data.json (live counts + cards). Both fetches start together. */

const BOOT = (document.currentScript && document.currentScript.dataset) || {};
const PAGE_SIZES = [15, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 25;
const COLLAPSED_CHIPS = 5;   // chips shown in a long filter row until its toggle is clicked

function prefGet(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } }
function prefSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

/* ── State ──────────────────────────────────────────────────────────────── */
let PAPERS = [];
let dataReady = false;
let TAG_BLOCKLIST = new Set();
function isTopicTag(t) { return !TAG_BLOCKLIST.has(t.toLowerCase()); }

const state = {
  type: 'all', preprint: false, ru: false, collab: '', tags: new Set(),
  year: 'all', added: 'all', search: '',
  page: 1,
  pageSize: (() => { const n = parseInt(prefGet('rg_page_size', ''), 10); return PAGE_SIZES.includes(n) ? n : DEFAULT_PAGE_SIZE; })(),
};

/* ── Top picks (highest-scored 4 from the past 7 days) ──────────────────── */
let TOP_PICK_IDS = new Set();
function isTopPick(p) { return TOP_PICK_IDS.size > 0 && TOP_PICK_IDS.has(p.doi || p.title || ''); }
function computeTopPicks(papers) {
  const latest = papers.reduce((max, p) => (p.added || '') > max ? (p.added || '') : max, '');
  const d = new Date(latest || new Date()); d.setDate(d.getDate() - 7);
  const cutoff = d.toISOString().slice(0, 10);
  const recent = papers.filter(p => (p.added || '') >= cutoff).sort((a, b) => (b.score || 0) - (a.score || 0));
  TOP_PICK_IDS = new Set(recent.slice(0, 4).map(p => p.doi || p.title || ''));
}

/* ── Filter dimensions ──────────────────────────────────────────────────────
   Each dimension has passes(p) (does the paper satisfy the current selection?) and
   keys(p) (which chip keys the paper belongs to). compute() uses both for live counts. */
const today = new Date();
function daysAgo(n) { const d = new Date(today); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); }
const ADDED_RANGES = [
  { label: 'All', key: 'all' },
  { label: 'Last 30 days', key: '30' },
  { label: 'Last 3 months', key: '90' },
  { label: 'Last 6 months', key: '180' },
  { label: 'This year', key: 'year' },
];
const ADDED_CUTOFF = Object.fromEntries(ADDED_RANGES.map(r => [r.key,
  r.key === 'all' ? '' : r.key === 'year' ? String(today.getFullYear()) + '-01-01' : daysAgo(parseInt(r.key, 10))]));

const typeOf = p => p.type || 'research';
const yearOf = p => String(p.year || '').trim();
const DIMS = {
  type:   { passes: p => state.type === 'all' || typeOf(p) === state.type,
            keys:   p => ['all', typeOf(p)] },
  status: { passes: p => !state.preprint || !!p.preprint,
            keys:   p => p.preprint ? ['all', 'preprint'] : ['all'] },
  picks:  { passes: p => !state.ru || !!p.ru_pick,
            keys:   p => p.ru_pick ? ['all', 'ru'] : ['all'] },
  collab: { passes: p => state.collab ? p.vip_author === state.collab : !p.vip_only,
            keys:   p => { const k = p.vip_only ? [] : ['all']; if (p.vip_author) k.push(p.vip_author); return k; } },
  tags:   { passes: p => state.tags.size === 0 || (p.tags || []).some(t => state.tags.has(t)),
            keys:   p => (p.tags || []).filter(isTopicTag) },
  year:   { passes: p => state.year === 'all' || yearOf(p) === state.year,
            keys:   p => yearOf(p) ? ['all', yearOf(p)] : ['all'] },
  added:  { passes: p => state.added === 'all' || (p.added || '') >= ADDED_CUTOFF[state.added],
            keys:   p => ADDED_RANGES.filter(r => r.key === 'all' || (p.added || '') >= ADDED_CUTOFF[r.key]).map(r => r.key) },
};
const DIM_NAMES = Object.keys(DIMS);

function isActive(dim, key) {
  switch (dim) {
    case 'type':   return state.type === key;
    case 'status': return key === 'all' ? !state.preprint : state.preprint;
    case 'picks':  return key === 'all' ? !state.ru : state.ru;
    case 'collab': return key === 'all' ? !state.collab : state.collab === key;
    case 'tags':   return state.tags.has(key);
    case 'year':   return state.year === key;
    case 'added':  return state.added === key;
  }
  return false;
}

function setFilter(dim, key) {
  switch (dim) {
    case 'type':   state.type = key; break;
    case 'status': state.preprint = key === 'preprint'; break;
    case 'picks':  state.ru = key === 'ru'; break;
    case 'collab': state.collab = key === 'all' ? '' : key; break;
    case 'tags':   if (state.tags.has(key)) state.tags.delete(key); else state.tags.add(key); break;
    case 'year':   state.year = key; break;
    case 'added':  state.added = key; break;
  }
  state.page = 1;
  update();
}

/* One pass over PAPERS: the filtered list plus, for every chip, how many papers would match if that
   chip were selected (all *other* active filters and the search still applied). A paper failing
   exactly one dimension counts toward that dimension's chips only; failing two or more counts nowhere. */
function compute() {
  const counts = {};
  DIM_NAMES.forEach(d => { counts[d] = Object.create(null); });
  const bump = (d, keys) => keys.forEach(k => { counts[d][k] = (counts[d][k] || 0) + 1; });
  const q = state.search;
  const filtered = [];
  for (const p of PAPERS) {
    let failed = null, nFail = 0;
    for (const d of DIM_NAMES) {
      if (!DIMS[d].passes(p)) { failed = d; if (++nFail > 1) break; }
    }
    if (nFail < 2 && q && !p._hay.includes(q)) { failed = 'search'; nFail++; }
    if (nFail === 0) {
      filtered.push(p);
      DIM_NAMES.forEach(d => bump(d, DIMS[d].keys(p)));
    } else if (nFail === 1 && failed !== 'search') {
      bump(failed, DIMS[failed].keys(p));
    }
  }
  return { filtered, counts };
}

/* ── Filter UI ──────────────────────────────────────────────────────────── */
const ROW_IDS = { type: 'type-filters', status: 'preprint-filters', picks: 'ru-filters', collab: 'collab-filters', tags: 'tag-filters', year: 'year-filters', added: 'added-filters' };
const chipReg = {};   // dim -> Map(key -> { el, countEl })
const rowCfg = {};    // dim -> { btn, expanded }   (only rows long enough to collapse)
let rowPrefs = {};
try { rowPrefs = JSON.parse(prefGet('rg_rows_expanded', '{}')) || {}; } catch (e) {}

function addChip(dim, key, label, count) {
  const el = document.createElement('button');
  el.type = 'button'; el.className = 'chip';
  const countEl = document.createElement('span');
  countEl.className = 'count'; countEl.textContent = count == null ? '' : count;
  el.append(label, countEl);
  el.addEventListener('click', () => setFilter(dim, key));
  document.getElementById(ROW_IDS[dim]).appendChild(el);
  if (!chipReg[dim]) chipReg[dim] = new Map();
  chipReg[dim].set(key, { el, countEl });
}
function hideRow(dim) { document.getElementById(ROW_IDS[dim]).classList.add('is-empty'); }

function initRowToggle(dim) {
  const reg = chipReg[dim];
  if (!reg || reg.size - (reg.has('all') ? 1 : 0) <= COLLAPSED_CHIPS) return;
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'row-toggle';
  const cfg = rowCfg[dim] = { btn, expanded: !!rowPrefs[dim] };
  btn.addEventListener('click', () => {
    cfg.expanded = !cfg.expanded;
    rowPrefs[dim] = cfg.expanded;
    prefSet('rg_rows_expanded', JSON.stringify(rowPrefs));
    applyRowCollapse(dim);
  });
  document.getElementById(ROW_IDS[dim]).querySelector('.filter-head').appendChild(btn);
}

// Collapsed rows show the first few chips plus any active ones, so a selection is never hidden.
function applyRowCollapse(dim) {
  const cfg = rowCfg[dim];
  if (!cfg) return;
  let idx = 0, hidden = 0;
  chipReg[dim].forEach((c, key) => {
    if (key === 'all') return;
    const show = cfg.expanded || idx < COLLAPSED_CHIPS || isActive(dim, key);
    c.el.classList.toggle('is-hidden', !show);
    if (!show) hidden++;
    idx++;
  });
  cfg.btn.textContent = cfg.expanded ? '− Less' : '…' + (hidden ? ' +' + hidden : '');
  cfg.btn.title = cfg.expanded ? 'Show fewer options' : 'Show all options';
  cfg.btn.setAttribute('aria-expanded', String(cfg.expanded));
}

function buildFilters(F) {
  TAG_BLOCKLIST = new Set(F.tagBlocklist || []);
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
  F.types.forEach(t => addChip('type', t, t === 'all' ? 'All' : cap(t), F.typeCounts[t]));
  if (F.hasPreprint) { addChip('status', 'all', 'All'); addChip('status', 'preprint', 'Preprint'); } else hideRow('status');
  addChip('picks', 'all', 'All');
  addChip('picks', 'ru', "✨ Ru's Picks");
  if (F.authors.length) {
    addChip('collab', 'all', 'All');
    F.authors.forEach(a => addChip('collab', a.name, a.name, a.count));
  } else hideRow('collab');
  if (F.tags.length) F.tags.forEach(t => addChip('tags', t.name, t.name, t.count)); else hideRow('tags');
  addChip('year', 'all', 'All', F.total);
  F.years.forEach(y => addChip('year', y.name, y.name, y.count));
  ADDED_RANGES.forEach(r => addChip('added', r.key, r.label));
  DIM_NAMES.forEach(initRowToggle);
  update();
}

// Active state, live counts and row collapsing; counts are null until the data has loaded.
function syncChips(counts) {
  DIM_NAMES.forEach(dim => {
    const reg = chipReg[dim];
    if (!reg) return;
    reg.forEach((c, key) => {
      const active = isActive(dim, key);
      c.el.classList.toggle('active', active);
      if (counts) {
        const n = counts[dim][key] || 0;
        c.countEl.textContent = n;
        c.el.classList.toggle('zero', n === 0 && !active);
      }
    });
    applyRowCollapse(dim);
  });
}

function activeFilterCount() {
  return (state.type !== 'all' ? 1 : 0) + (state.preprint ? 1 : 0) + (state.ru ? 1 : 0) + (state.collab ? 1 : 0)
    + state.tags.size + (state.year !== 'all' ? 1 : 0) + (state.added !== 'all' ? 1 : 0);
}

/* ── Whole-panel minimize (filters stay applied while hidden) ───────────── */
const filtersEl = document.querySelector('.filters');
const filtersToggle = document.getElementById('filters-toggle');
function setFiltersCollapsed(collapsed) {
  filtersEl.classList.toggle('collapsed', collapsed);
  filtersToggle.setAttribute('aria-expanded', String(!collapsed));
}
filtersToggle.addEventListener('click', () => {
  const collapsed = !filtersEl.classList.contains('collapsed');
  setFiltersCollapsed(collapsed);
  prefSet('rg_filters_min', collapsed ? '1' : '0');
});
if (prefGet('rg_filters_min', '0') === '1') setFiltersCollapsed(true);

/* ── Search (debounced) ─────────────────────────────────────────────────── */
let searchTimer;
document.getElementById('search').addEventListener('input', e => {
  const v = e.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.search = v.toLowerCase().trim(); state.page = 1; update(); }, 150);
});

/* ── Tag clicks inside grid ─────────────────────────────────────────────── */
const grid = document.getElementById('grid');
grid.addEventListener('click', e => {
  const tag = e.target.dataset && e.target.dataset.clicktag;
  if (tag) setFilter('tags', tag);
});


/* ── Toast notifications ─────────────────────────────────────────────────── */
function showToast(msg, type = 'success', duration = 8000) {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  const icon = type === 'success' ? '✓' : '✕';
  t.innerHTML = '<span>' + icon + ' ' + msg.replace(/</g,'&lt;') + '</span>'
    + '<button class="toast-close" aria-label="Close">&times;</button>';
  t.querySelector('.toast-close').addEventListener('click', () => t.remove());
  c.appendChild(t);
  setTimeout(() => { if (t.parentNode) t.remove(); }, duration);
}

/* ── Notes storage (localStorage) ───────────────────────────────────────── */
function noteKey(p) { return 'note:' + (p.doi || p.title || '').slice(0, 120); }
function getNote(p) { try { return localStorage.getItem(noteKey(p)) || ''; } catch(e) { return ''; } }
function saveNoteByKey(k, v) { try { localStorage.setItem(k, v); } catch(e) {} }

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
  const badgeClass = 'badge-'+(type==='review'?'review':type==='perspective'?'perspective':type==='article'?'article':'research');
  const paperUrl = (p.doi ? 'https://doi.org/'+p.doi : p.link) || '';
  const titleHtml = paperUrl ? '<a href="'+esc(paperUrl)+'" target="_blank" rel="noopener">'+esc(p.title)+'</a>' : esc(p.title);
  let authorHtml;
  if (p.author_data && p.author_data.length) {
    authorHtml = p.author_data.map(a => {
      const name = a.name || '';
      if (!name) return '';
      const href = a.orcid
        ? 'https://orcid.org/' + esc(a.orcid)
        : authorLink(name);
      return '<a class="author-link" href="'+href+'" target="_blank" rel="noopener">'+esc(name)+'</a>';
    }).filter(Boolean).join('');
  } else {
    const rawAuthors = typeof p.authors === 'string' ? p.authors : (p.authors||[]).join(', ');
    const authorNames = rawAuthors.split(/,\s*et al\.?/).map(s=>s.trim()).join('').split(/,\s*/).map(s=>s.trim()).filter(Boolean);
    authorHtml = authorNames.map(a => {
      const name = a.replace(/\s*et al\.?\s*$/,'').trim();
      return name ? '<a class="author-link" href="'+authorLink(name)+'" target="_blank" rel="noopener">'+esc(name)+'</a>' : '';
    }).filter(Boolean).join('');
  }
  const tags = (p.tags||[]).filter(isTopicTag).map(t=>'<span class="tag" data-clicktag="'+esc(t)+'">'+esc(t)+'</span>').join('');
  const added = p.added ? '<span class="card-date">added '+p.added+'</span>' : '';
  const jUrl = journalUrl(p.journal);
  const journalHtml = p.journal ? (jUrl ? '<a class="journal-link" href="'+esc(jUrl)+'" target="_blank" rel="noopener">'+esc(p.journal)+'</a>' : esc(p.journal)) : '';
  const venue = [journalHtml, p.year ? esc(p.year) : ''].filter(Boolean).join(' · ');
  const pdfSlug = (p.doi ? p.doi.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') : (p.title||'paper').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60)) + '.pdf';
  const pdfBtn = p.pdf_link ? '<a class="btn-pdf" href="'+esc(p.pdf_link)+'" target="_blank" rel="noopener">&#8595; PDF</a>'
    : '<div class="btn-add-pdf" role="button" tabindex="0" data-addpdf="1" data-pdfslug="'+esc(pdfSlug)+'">＋ Add PDF'
        +'<div class="pdf-popover" onclick="event.stopPropagation()">'
          +'<div class="pdf-popover-title">Upload PDF for this paper</div>'
          +'<label class="pdf-file-label" onclick="event.stopPropagation()">'
            +'<input type="file" accept=".pdf" class="pdf-file-input">'
            +'&#128194; Choose file…'
          +'</label>'
          +'<div class="pdf-selected-name"></div>'
          +'<button class="pdf-upload-btn" onclick="handlePdfUpload(this,event)">&#8593; Upload</button>'
          +'<div class="pdf-upload-status"></div>'
        +'</div>'
      +'</div>';
  const existingNote = getNote(p);
  const hasNote = existingNote.trim().length > 0;
  const nk = noteKey(p);
  const noteId = 'note-' + Math.random().toString(36).slice(2);
  const starHtml = isTopPick(p) ? '<div class="top-pick-star" title="Top pick · recommended for printing">⭐</div>' : '';
  const preprintBadge = p.preprint ? '<span class="badge badge-preprint">preprint</span>' : '';
  const collabBadge = p.vip_author ? '<span class="badge badge-collab" title="Paper by collaborator '+esc(p.vip_author)+'">&#128101; '+esc(p.vip_author)+'</span>' : '';
  const ruBadge = p.ru_pick ? '<span class="ru-badge">&#10024; Ru\'s Picks</span>' : '';
  return '<div class="card">'
    +'<div class="card-meta"><span class="badge '+badgeClass+'">'+esc(type)+'</span>'+preprintBadge+collabBadge+ruBadge+added+'</div>'
    +'<div class="card-title">'+titleHtml+'</div>'
    +(authorHtml ? '<div class="card-authors">'+authorHtml+'</div>' : '')
    +(venue ? '<div class="card-venue">'+venue+'</div>' : '')
    +(p.summary ? '<div class="card-summary">'+esc(p.summary)+'</div>' : '')
    +(p.relevance ? '<div class="card-relevance"><div class="card-relevance-label">Cell Science relevance</div><div class="card-relevance-text">'+esc(p.relevance)+'</div></div>' : '')
    +(tags ? '<div class="card-tags">'+tags+'</div>' : '')
    +'<div class="card-actions">'+pdfBtn+'</div>'
    +'<div class="notes-section">'
      +'<button class="notes-toggle'+(hasNote?' has-notes':'')+'" data-noteid="'+noteId+'">'
        +(hasNote ? '&#128221; Notes' : '+ Add note')
      +'</button>'
      +'<div class="notes-area'+(hasNote?' open':'')+'" id="'+noteId+'" data-nk="'+esc(nk)+'">'
        +'<textarea class="notes-textarea" rows="3" placeholder="Your notes…">'+esc(existingNote)+'</textarea>'
        +'<div class="notes-saved"></div>'
      +'</div>'
    +'</div>'
    +starHtml
    +'</div>';
}

/* ── Notes + PDF upload interaction ───────────────────────────────────────── */
document.getElementById('grid').addEventListener('change', e => {
  const input = e.target.closest('.pdf-file-input');
  if (!input) return;
  const file = input.files[0];
  const popover = input.closest('.pdf-popover');
  if (!popover) return;
  const nameEl = popover.querySelector('.pdf-selected-name');
  const status = popover.querySelector('.pdf-upload-status');
  if (nameEl) nameEl.textContent = file ? file.name : '';
  if (status) { status.textContent = file ? 'Ready to upload.' : ''; status.style.color = ''; }
});

async function handlePdfUpload(btn, event) {
  event.stopPropagation();
  const popover = btn.closest('.pdf-popover');
  const status = popover ? popover.querySelector('.pdf-upload-status') : null;
  const fileInput = popover ? popover.querySelector('.pdf-file-input') : null;
  const file = fileInput && fileInput.files[0];
  if (!file) {
    if (status) { status.textContent = 'Please choose a PDF file first.'; status.style.color = '#b91c1c'; }
    return;
  }
  const addBtn = btn.closest('[data-addpdf]');
  const slug = addBtn ? addBtn.dataset.pdfslug : null;
  if (!slug) return;
  const token = getToken();
  if (!token) {
    if (addBtn) addBtn.classList.remove('open');
    addModal.classList.add('open');
    showTokenScreen();
    return;
  }
  btn.disabled = true;
  if (status) { status.textContent = 'Uploading…'; status.style.color = ''; }
  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = reader.result.split(',')[1];
    try {
      const resp = await fetch(
        'https://api.github.com/repos/ismi-ops/literature-rg/contents/pdfs/' + encodeURIComponent(slug),
        {
          method: 'PUT',
          headers: {
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: 'chore: upload PDF via site', content: b64 }),
        }
      );
      if (resp.ok) {
        if (status) { status.textContent = '✓ Uploaded!'; status.style.color = '#16a34a'; }
        if (addBtn) addBtn.classList.remove('open');
        showToast('PDF uploaded — button will appear on this card in ~1 min.', 'success', 10000);
      } else {
        const err = await resp.json().catch(() => ({}));
        let msg;
        if (resp.status === 401) msg = 'Invalid token — click "Change token" in the ＋ Add Paper modal to update it.';
        else if (resp.status === 403) msg = 'Token lacks Contents permission — regenerate your PAT and enable Contents (R&W). Click "Change token" in the ＋ Add Paper modal.';
        else if (resp.status === 422) msg = (err.message || '').includes('sha') ? 'This PDF was already uploaded. Reload the page — the PDF button should appear.' : 'Upload error 422: ' + (err.message || 'invalid request.');
        else msg = 'Upload error ' + resp.status + ': ' + (err.message || 'unknown.');
        if (status) status.textContent = msg;
        showToast(msg, 'error', 12000);
        btn.disabled = false;
      }
    } catch (err) {
      const msg = 'Upload failed: ' + err.message;
      if (status) status.textContent = msg;
      showToast(msg, 'error', 12000);
      btn.disabled = false;
    }
  };
  reader.readAsDataURL(file);
}

document.getElementById('grid').addEventListener('click', e => {
  const addBtn = e.target.closest('[data-addpdf]');
  if (addBtn) {
    e.stopPropagation();
    const wasOpen = addBtn.classList.contains('open');
    document.querySelectorAll('.btn-add-pdf.open').forEach(b => b.classList.remove('open'));
    if (!wasOpen) addBtn.classList.add('open');
    return;
  }
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
document.addEventListener('click', () => {
  document.querySelectorAll('.btn-add-pdf.open').forEach(b => b.classList.remove('open'));
});
document.getElementById('grid').addEventListener('input', e => {
  if (!e.target.classList.contains('notes-textarea')) return;
  const area = e.target.closest('.notes-area');
  if (!area) return;
  const k = area.dataset.nk;
  if (!k) return;
  saveNoteByKey(k, e.target.value);
  const saved = area.querySelector('.notes-saved');
  if (saved) saved.textContent = 'Saved';
  const noteId = area.id;
  const toggle = document.querySelector('[data-noteid="'+noteId+'"]');
  if (toggle) {
    const hasNote = e.target.value.trim().length > 0;
    toggle.classList.toggle('has-notes', hasNote);
    toggle.textContent = hasNote ? '📑 Notes' : '+ Add note';
  }
});

/* ── Pagination + render ────────────────────────────────────────────────── */
const PAGE_GAP = '…';
function pageItems(cur, last) {
  const set = new Set([1, last]);
  for (let i = cur - 2; i <= cur + 2; i++) if (i > 1 && i < last) set.add(i);
  const nums = [...set].sort((a, b) => a - b), out = [];
  nums.forEach((n, i) => { if (i && n - nums[i - 1] > 1) out.push(PAGE_GAP); out.push(n); });
  return out;
}
function renderPager(pages) {
  const el = document.getElementById('pager');
  if (pages <= 1) { el.innerHTML = ''; return; }
  const cur = state.page;
  el.innerHTML = '<button type="button" class="page-btn" data-page="' + (cur - 1) + '"' + (cur === 1 ? ' disabled' : '') + '>‹ Prev</button>'
    + pageItems(cur, pages).map(n => n === PAGE_GAP
        ? '<span class="page-gap">' + PAGE_GAP + '</span>'
        : '<button type="button" class="page-btn' + (n === cur ? ' active' : '') + '" data-page="' + n + '"' + (n === cur ? ' aria-current="page"' : '') + '>' + n + '</button>').join('')
    + '<button type="button" class="page-btn" data-page="' + (cur + 1) + '"' + (cur === pages ? ' disabled' : '') + '>Next ›</button>';
}
document.getElementById('pager').addEventListener('click', e => {
  const b = e.target.closest('[data-page]');
  if (!b || b.disabled) return;
  state.page = parseInt(b.dataset.page, 10);
  update();
  window.scrollTo(0, 0);
});

const pageSizeSel = document.getElementById('page-size');
PAGE_SIZES.forEach(n => { const o = document.createElement('option'); o.value = n; o.textContent = n; pageSizeSel.appendChild(o); });
pageSizeSel.value = state.pageSize;
pageSizeSel.addEventListener('change', () => {
  state.pageSize = parseInt(pageSizeSel.value, 10);
  prefSet('rg_page_size', String(state.pageSize));
  state.page = 1;
  update();
});

// Only the current page of cards is ever turned into DOM, however many papers match.
function renderPage(filtered) {
  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / state.pageSize));
  if (state.page > pages) state.page = pages;
  const start = (state.page - 1) * state.pageSize;
  const slice = filtered.slice(start, start + state.pageSize);
  grid.innerHTML = slice.length ? slice.map(p => fmt(p)).join('') : '<div class="empty">No papers match your filters.</div>';
  document.getElementById('result-count').textContent = total + ' paper' + (total === 1 ? '' : 's');
  document.getElementById('range-label').textContent = total ? 'Showing ' + (start + 1) + '–' + (start + slice.length) + ' of ' + total : '';
  renderPager(pages);
}

function update() {
  let counts = null;
  if (dataReady) {
    const r = compute();
    counts = r.counts;
    renderPage(r.filtered);
  }
  syncChips(counts);
  const n = activeFilterCount();
  document.getElementById('filters-badge').textContent = n ? n + ' active' : '';
}

/* ── Boot ───────────────────────────────────────────────────────────────── */
async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url.split('?')[0] + ' returned HTTP ' + r.status);
  return r.json();
}
function showLoadError(err) {
  grid.innerHTML = '<div class="empty">Could not load papers (' + esc(err.message) + '). '
    + 'Try reloading; if you opened this file straight from disk, serve it over http(s) instead.</div>';
}
async function boot() {
  const filtersReq = fetchJSON(BOOT.filters || 'filters.json');
  const papersReq = fetchJSON(BOOT.papers || 'papers_data.json');
  papersReq.catch(() => {});   // handled below; stops an unhandled-rejection warning if filters fail first
  try {
    buildFilters(await filtersReq);
    PAPERS = await papersReq;
  } catch (err) { showLoadError(err); return; }
  PAPERS.forEach(p => { p._hay = [p.title, p.authors, p.journal, p.summary, ...(p.tags || [])].join(' ').toLowerCase(); });
  computeTopPicks(PAPERS);
  dataReady = true;
  update();
}

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
  const ruPick = document.getElementById('ru-pick-check').checked;
  const inputs = isDOI ? { doi: raw, url: '', ru_pick: ruPick ? 'true' : 'false' } : { url: raw, doi: '', ru_pick: ruPick ? 'true' : 'false' };

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
      document.getElementById('ru-pick-check').checked = false;
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

boot();
