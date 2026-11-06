/* app.js — Ru's Reading List.
   Boot order: index.html shell (+ inline password gate) -> this script -> filters.json (builds the
   filter UI) -> papers_data.json (live counts + cards). Both fetches start together. */

const BOOT = (document.currentScript && document.currentScript.dataset) || {};
const PAGE_SIZES = [15, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 25;

function prefGet(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } }
function prefSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

/* ── State ──────────────────────────────────────────────────────────────── */
let PAPERS = [];
let dataReady = false;
let TAG_BLOCKLIST = new Set();
function isTopicTag(t) { return !TAG_BLOCKLIST.has(t.toLowerCase()); }

const state = {
  search: '',
  page: 1,
  pageSize: (() => { const n = parseInt(prefGet('rg_page_size', ''), 10); return PAGE_SIZES.includes(n) ? n : DEFAULT_PAGE_SIZE; })(),
};

/* ── Top picks: the agent's 4 highest-scored papers from the past 7 days, starred as "recommended
   for printing". Papers Ru sent are already being printed, so they are never starred or counted. */
let TOP_PICK_IDS = new Set();
function isTopPick(p) { return !p.ru_pick && TOP_PICK_IDS.size > 0 && TOP_PICK_IDS.has(p.doi || p.title || ''); }
function computeTopPicks(papers) {
  const latest = papers.reduce((max, p) => (p.added || '') > max ? (p.added || '') : max, '');
  const d = new Date(latest || new Date()); d.setDate(d.getDate() - 7);
  const cutoff = d.toISOString().slice(0, 10);
  const recent = papers.filter(p => !p.ru_pick && (p.added || '') >= cutoff).sort((a, b) => (b.score || 0) - (a.score || 0));
  TOP_PICK_IDS = new Set(recent.slice(0, 4).map(p => p.doi || p.title || ''));
}

/* ── Filter dimensions ──────────────────────────────────────────────────────
   sel[dim] is the set of selected option keys (empty = no restriction). Within a dimension the
   selections are OR'd; across dimensions they are AND'd.
   passes(p): does the paper satisfy the current selection of this dimension?
   keys(p):   which option keys does the paper belong to? (drives the live counts) */
const today = new Date();
function daysAgo(n) { const d = new Date(today); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); }
const ADDED_RANGES = [
  { label: 'Any time', key: 'all' },
  { label: 'Last 30 days', key: '30' },
  { label: 'Last 3 months', key: '90' },
  { label: 'Last 6 months', key: '180' },
  { label: 'This year', key: 'year' },
];
const ADDED_CUTOFF = Object.fromEntries(ADDED_RANGES.map(r => [r.key,
  r.key === 'all' ? '' : r.key === 'year' ? String(today.getFullYear()) + '-01-01' : daysAgo(parseInt(r.key, 10))]));

const typeOf = p => p.type || 'research';
const yearOf = p => String(p.year || '').trim();
// Property order is the order the dropdowns appear in.
const DIMS = {
  type:   { label: 'Type',
            passes: p => !sel.type.size || sel.type.has(typeOf(p)),
            keys:   p => [typeOf(p)] },
  status: { label: 'Status',
            passes: p => !sel.status.size || !!p.preprint,
            keys:   p => p.preprint ? ['preprint'] : [] },
  picks:  { label: 'Picks',
            passes: p => !sel.picks.size || sel.picks.has(p.ru_pick ? 'ru' : 'agent'),
            keys:   p => [p.ru_pick ? 'ru' : 'agent'] },
  collab: { label: 'Collaborators',
            passes: p => sel.collab.size ? sel.collab.has(p.vip_author) : !p.vip_only,
            keys:   p => p.vip_author ? [p.vip_author] : [] },
  tags:   { label: 'Topic',
            passes: p => !sel.tags.size || (p.tags || []).some(t => sel.tags.has(t)),
            keys:   p => (p.tags || []).filter(isTopicTag) },
  year:   { label: 'Year',
            passes: p => !sel.year.size || sel.year.has(yearOf(p)),
            keys:   p => yearOf(p) ? [yearOf(p)] : [] },
  added:  { label: 'Added', single: true,   // ranges overlap, so pick one
            passes: p => !sel.added.size || (p.added || '') >= ADDED_CUTOFF[[...sel.added][0]],
            keys:   p => ADDED_RANGES.filter(r => r.key === 'all' || (p.added || '') >= ADDED_CUTOFF[r.key]).map(r => r.key) },
  pdf:    { label: 'PDF', admin: true,      // only shown when a GitHub token is saved (the site owner)
            passes: p => !sel.pdf.size || !hasPdf(p),
            keys:   p => hasPdf(p) ? [] : ['missing'] },
};
const DIM_NAMES = Object.keys(DIMS);
const sel = Object.fromEntries(DIM_NAMES.map(d => [d, new Set()]));

function isActive(dim, key) { return key === 'all' ? sel[dim].size === 0 : sel[dim].has(key); }

function setFilter(dim, key) {
  const s = sel[dim];
  if (DIMS[dim].single) { s.clear(); if (key !== 'all') s.add(key); }
  else if (s.has(key)) s.delete(key);
  else s.add(key);
  state.page = 1;
  update();
}
function clearFilters() {
  DIM_NAMES.forEach(d => sel[d].clear());
  state.page = 1;
  update();
}
function activeFilterCount() { return DIM_NAMES.reduce((n, d) => n + sel[d].size, 0); }

/* One pass over PAPERS: the filtered list plus, for every option, how many papers would match if
   that option were selected (all *other* dimensions and the search still applied). A paper failing
   exactly one dimension counts toward that dimension's options only; failing two or more counts nowhere. */
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

/* ── Filter UI: one multiselect dropdown per dimension ──────────────────── */
const ddReg = {};     // dim -> { wrap, btn, nEl, panel }
const chipReg = {};   // dim -> Map(key -> { row, input, countEl })

function makeDropdown(dim) {
  const wrap = document.createElement('div');
  wrap.className = 'dd';
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'dd-btn';
  btn.setAttribute('aria-haspopup', 'true'); btn.setAttribute('aria-expanded', 'false');
  const nEl = document.createElement('span'); nEl.className = 'dd-n';
  const caret = document.createElement('span'); caret.className = 'dd-caret'; caret.textContent = '▾';
  btn.append(DIMS[dim].label, nEl, caret);
  const panel = document.createElement('div');
  panel.className = 'dd-panel'; panel.setAttribute('role', 'group'); panel.setAttribute('aria-label', DIMS[dim].label);
  wrap.append(btn, panel);
  btn.addEventListener('click', () => toggleDropdown(dim));
  document.getElementById('filter-bar').appendChild(wrap);
  ddReg[dim] = { wrap, btn, nEl, panel };
  chipReg[dim] = new Map();
}

function addOption(dim, key, label, count) {
  const row = document.createElement('label');
  row.className = 'dd-opt';
  const input = document.createElement('input');
  input.type = DIMS[dim].single ? 'radio' : 'checkbox';
  input.name = 'f-' + dim;
  input.addEventListener('change', () => setFilter(dim, key));
  const text = document.createElement('span'); text.className = 'dd-label'; text.textContent = label;
  const countEl = document.createElement('span'); countEl.className = 'count'; countEl.textContent = count == null ? '' : count;
  row.append(input, text, countEl);
  ddReg[dim].panel.appendChild(row);
  chipReg[dim].set(key, { row, input, countEl });
}
function hideDropdown(dim) { ddReg[dim].wrap.classList.add('is-empty'); }

function setOpen(dim, open) {
  const d = ddReg[dim];
  d.wrap.classList.toggle('open', open);
  d.btn.setAttribute('aria-expanded', String(open));
  if (open) {   // keep the panel on screen on narrow viewports
    d.wrap.classList.remove('align-right');
    if (d.panel.getBoundingClientRect().right > window.innerWidth - 8) d.wrap.classList.add('align-right');
  }
}
function closeDropdowns(except) {
  DIM_NAMES.forEach(d => { if (d !== except && ddReg[d] && ddReg[d].wrap.classList.contains('open')) setOpen(d, false); });
}
function toggleDropdown(dim) {
  const open = !ddReg[dim].wrap.classList.contains('open');
  closeDropdowns(open ? dim : null);
  setOpen(dim, open);
}
document.addEventListener('click', e => { if (!e.target.closest('.dd')) closeDropdowns(); });
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const open = DIM_NAMES.find(d => ddReg[d] && ddReg[d].wrap.classList.contains('open'));
  if (open) { closeDropdowns(); ddReg[open].btn.focus(); }
});

// The "no PDF" filter is for the site owner: it appears only when a GitHub token is saved in this browser.
function syncAdminFilters() {
  DIM_NAMES.filter(d => DIMS[d].admin && ddReg[d]).forEach(d => {
    const show = !!getToken();
    ddReg[d].wrap.classList.toggle('is-empty', !show);
    if (!show) sel[d].clear();
  });
  if (dataReady) update();   // also (re)draws the gear menus on the cards
}

function buildFilters(F) {
  TAG_BLOCKLIST = new Set(F.tagBlocklist || []);
  DIM_NAMES.forEach(makeDropdown);
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
  F.types.filter(t => t !== 'all').forEach(t => addOption('type', t, cap(t), F.typeCounts[t]));
  if (F.hasPreprint) addOption('status', 'preprint', 'Preprint'); else hideDropdown('status');
  addOption('picks', 'ru', "✨ Ru's Picks");
  addOption('picks', 'agent', 'Agent picks');
  if (F.authors.length) F.authors.forEach(a => addOption('collab', a.name, a.name, a.count)); else hideDropdown('collab');
  if (F.tags.length) F.tags.forEach(t => addOption('tags', t.name, t.name, t.count)); else hideDropdown('tags');
  F.years.forEach(y => addOption('year', y.name, y.name, y.count));
  ADDED_RANGES.forEach(r => addOption('added', r.key, r.label));
  addOption('pdf', 'missing', 'No PDF');
  syncAdminFilters();
  update();
}

// Checkbox state, live counts and button badges; counts is null until the data has loaded.
function syncChips(counts) {
  DIM_NAMES.forEach(dim => {
    if (!chipReg[dim]) return;
    chipReg[dim].forEach((c, key) => {
      const on = isActive(dim, key);
      c.input.checked = on;
      c.row.classList.toggle('checked', on);
      if (counts) {
        const n = counts[dim][key] || 0;
        c.countEl.textContent = n;
        c.row.classList.toggle('zero', n === 0 && !on);
      }
    });
    const n = sel[dim].size;
    ddReg[dim].nEl.textContent = n ? String(n) : '';
    ddReg[dim].btn.classList.toggle('has-sel', n > 0);
  });
}

/* ── Whole-bar minimize (filters stay applied while hidden) ─────────────── */
const filtersEl = document.querySelector('.filters');
const filtersToggle = document.getElementById('filters-toggle');
function setFiltersCollapsed(collapsed) {
  if (collapsed) closeDropdowns();
  filtersEl.classList.toggle('collapsed', collapsed);
  filtersToggle.setAttribute('aria-expanded', String(!collapsed));
}
filtersToggle.addEventListener('click', () => {
  const collapsed = !filtersEl.classList.contains('collapsed');
  setFiltersCollapsed(collapsed);
  prefSet('rg_filters_min', collapsed ? '1' : '0');
});
document.getElementById('filters-clear').addEventListener('click', clearFilters);
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
function getNote(p) {
  try {
    let v = localStorage.getItem(noteKey(p)) || '';
    // A preprint that got published changes DOI: carry the note over from its earlier DOI.
    if (!v) for (const d of (p.previous_dois || [])) {
      const old = localStorage.getItem('note:' + d.slice(0, 120));
      if (old) { v = old; localStorage.setItem(noteKey(p), old); break; }
    }
    return v;
  } catch(e) { return ''; }
}
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
  const k = name.toLowerCase().trim();
  if (JOURNAL_URLS[k]) return JOURNAL_URLS[k];
  // "Science (New York, N.Y.)" -> "science", "Nature reviews. Genetics" -> "nature reviews genetics"
  const n = k.replace(/\s*\([^)]*\)/g, '').replace(/\.\s+/g, ' ').replace(/\.$/, '').replace(/\s+/g, ' ').trim();
  return JOURNAL_URLS[n] || '';
}

/* ── Link helpers ───────────────────────────────────────────────────────── */
// Only http(s) links or our own uploaded pdfs/*.pdf ever reach an href; http is upgraded to https.
function safeUrl(u) {
  u = String(u || '').trim().replace(/[>,;]+$/, '');
  if (/^pdfs\/[^?#]+\.pdf$/i.test(u)) return u;
  if (!/^https?:\/\//i.test(u)) return '';
  return u.replace(/^http:\/\//i, 'https://').replace(/^(https:\/\/)dx\.doi\.org\//i, '$1doi.org/');
}
// A "real" PDF: one we hold, or a URL that points straight at a PDF file (not an article/landing page).
function isDirectPdf(u) {
  if (!/^https?:\/\//i.test(u)) return true;
  const path = u.split(/[?#]/)[0].toLowerCase();
  return /\.pdf$/.test(path) || /\/(pdf|epdf|pdfdirect|pdfft|articlepdf)(\/|$)/.test(path) || /[?&]type=printable\b/i.test(u);
}
function hasPdf(p) { const u = safeUrl(p.pdf_link); return !!u && isDirectPdf(u); }

/* ── Card rendering ─────────────────────────────────────────────────────── */
function authorLink(name) { return 'https://scholar.google.com/scholar?q=' + encodeURIComponent(name); }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(p) {
  const type = (p.type||'research').toLowerCase();
  const badgeClass = 'badge-'+(type==='review'?'review':type==='perspective'?'perspective':type==='article'?'article':'research');
  const paperUrl = safeUrl(p.doi ? 'https://doi.org/'+p.doi : p.link);
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
  const pdfSlug = (p.doi ? p.doi.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') : (p.title||'paper').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60).replace(/-+$/,'')) + '.pdf';
  const pdfHref = safeUrl(p.pdf_link);
  const fullTextBtn = pdfHref && !hasPdf(p) ? '<a class="btn-fulltext" href="'+esc(pdfHref)+'" target="_blank" rel="noopener" title="Opens the article page (not a PDF file)">Full text &#8599;</a>' : '';
  const pdfBtn = hasPdf(p) ? '<a class="btn-pdf" href="'+esc(pdfHref)+'" target="_blank" rel="noopener">&#8595; PDF</a>'
    : '<div class="btn-add-pdf" role="button" tabindex="0" data-addpdf="1">＋ Add PDF'
        +'<div class="pdf-popover" data-pdfbox="1" onclick="event.stopPropagation()">'
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
  const adminTools = !!getToken();
  const starHtml = isTopPick(p) ? '<div class="top-pick-star" title="Top pick · recommended for printing">⭐</div>' : '';
  const preprintBadge = p.preprint ? '<span class="badge badge-preprint">preprint</span>' : '';
  const publishedBadge = p.published_on && p.published_on >= daysAgo(30)
    ? '<span class="badge badge-published" title="Formerly a preprint (' + esc((p.previous_dois || []).slice(-1)[0] || '') + '), now published">&#10003; Published</span>' : '';
  const collabBadge = p.vip_author ? '<span class="badge badge-collab" title="Paper by collaborator '+esc(p.vip_author)+'">&#128101; '+esc(p.vip_author)+'</span>' : '';
  const ruBadge = p.ru_pick ? '<span class="ru-badge">&#10024; Ru\'s Picks</span>' : '';
  return '<div class="card" data-key="'+esc(paperKey(p))+'" data-pdfslug="'+esc(pdfSlug)+'">'
    +'<div class="card-meta"><span class="badge '+badgeClass+'">'+esc(type)+'</span>'+preprintBadge+publishedBadge+collabBadge+ruBadge+added+'</div>'
    +'<div class="card-title">'+titleHtml+'</div>'
    +(authorHtml ? '<div class="card-authors">'+authorHtml+'</div>' : '')
    +(venue ? '<div class="card-venue">'+venue+'</div>' : '')
    +(p.summary ? '<div class="card-summary">'+esc(p.summary)+'</div>' : '')
    +(p.relevance ? '<div class="card-relevance"><div class="card-relevance-label">Cell Science relevance</div><div class="card-relevance-text">'+esc(p.relevance)+'</div></div>' : '')
    +(tags ? '<div class="card-tags">'+tags+'</div>' : '')
    +'<div class="card-actions">'+fullTextBtn+pdfBtn+'</div>'
    +'<div class="notes-section">'
      +'<button class="notes-toggle'+(hasNote?' has-notes':'')+'" data-noteid="'+noteId+'">'
        +(hasNote ? '&#128221; Notes' : '+ Add note')
      +'</button>'
      +'<div class="notes-area'+(hasNote?' open':'')+'" id="'+noteId+'" data-nk="'+esc(nk)+'">'
        +'<textarea class="notes-textarea" rows="3" placeholder="Your notes…">'+esc(existingNote)+'</textarea>'
        +'<div class="notes-saved"></div>'
      +'</div>'
    +'</div>'
    +(starHtml || adminTools ? '<div class="card-corner">'+starHtml+(adminTools ? gearHtml(p) : '')+'</div>' : '')
    +'</div>';
}

/* ── Owner tools: gear menu on every card (shown only when a GitHub token is saved) ─────────
   Edits (Ru's Picks, PDF link, remove) take effect instantly in this browser, then go out in one
   batch to the "Edit Papers" workflow, which updates papers.json and regenerates the site. */
const EDIT_WORKFLOW_URL = 'https://api.github.com/repos/ismi-ops/literature-rg/actions/workflows/edit_papers.yml/dispatches';
const EDIT_FLUSH_MS = 5000;                      // wait for a pause in clicking before sending
const EDIT_PENDING_TTL_MS = 2 * 60 * 60 * 1000;  // stop overlaying an edit the site never picked up
const EDIT_BATCH = 80;
let PAPER_BY_KEY = new Map();
function paperKey(p) { return p.doi || p.title || ''; }

function gearHtml(p) {
  const href = safeUrl(p.pdf_link);
  const shown = href.length > 46 ? href.slice(0, 30) + '…' + href.slice(-14) : href;
  return '<div class="card-gear">'
    + '<button type="button" class="gear-btn" data-act="gear" title="Edit this paper" aria-label="Edit this paper" aria-haspopup="true">&#9881;</button>'
    + '<div class="gear-panel" role="group" aria-label="Edit paper">'
      + '<label class="gear-check"><input type="checkbox" data-act="ru-pick"' + (p.ru_pick ? ' checked' : '') + '> &#10024; Ru\'s Picks</label>'
      + '<div class="gear-section" data-pdfbox="1">'
        + '<div class="gear-h">PDF</div>'
        + '<div class="gear-current">' + (href ? 'Now: <a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(shown) + '</a>' : 'No PDF link yet') + '</div>'
        + '<input type="url" class="gear-input" placeholder="Paste a link to the PDF (https://…)" aria-label="PDF link">'
        + '<div class="gear-row">'
          + '<button type="button" class="gear-btn2" data-act="save-link">Save link</button>'
          + (p.pdf_link ? '<button type="button" class="gear-btn2 ghost" data-act="clear-link">Remove link</button>' : '')
        + '</div>'
        + '<div class="gear-status"></div>'
        + '<div class="gear-or">or upload a file</div>'
        + '<label class="pdf-file-label"><input type="file" accept=".pdf" class="pdf-file-input">&#128194; Choose file…</label>'
        + '<div class="pdf-selected-name"></div>'
        + '<button type="button" class="pdf-upload-btn" onclick="handlePdfUpload(this,event)">&#8593; Upload</button>'
        + '<div class="pdf-upload-status"></div>'
      + '</div>'
      + '<button type="button" class="gear-delete" data-act="delete">&#128465; Remove from list</button>'
    + '</div>'
  + '</div>';
}

/* pendingEdits[key] = { patch, t, sent } — kept in localStorage so edits survive a reload until the
   regenerated site data reflects them. */
let pendingEdits = {};
try { pendingEdits = JSON.parse(prefGet('rg_pending_edits', '{}')) || {}; } catch (e) {}
let flushTimer = null;
function savePending() { prefSet('rg_pending_edits', JSON.stringify(pendingEdits)); }

function applyPatchLocally(p, patch) {
  if ('ru_pick' in patch) { if (patch.ru_pick) p.ru_pick = true; else delete p.ru_pick; }
  if ('pdf_link' in patch) p.pdf_link = patch.pdf_link;
  if (patch.delete) PAPERS = PAPERS.filter(x => x !== p);
}
function queueEdit(p, patch) {
  const key = paperKey(p);
  const cur = pendingEdits[key] || { patch: {}, t: 0, sent: false };
  Object.assign(cur.patch, patch);
  cur.t = Date.now(); cur.sent = false;
  pendingEdits[key] = cur;
  savePending();
  applyPatchLocally(p, patch);
  update();
  scheduleFlush();
}
function scheduleFlush() { clearTimeout(flushTimer); flushTimer = setTimeout(() => flushEdits(false), EDIT_FLUSH_MS); }

// Called once the freshly fetched data is in: drop edits the site already reflects, re-apply the rest.
function applyPendingEdits() {
  const byKey = new Map(PAPERS.map(p => [paperKey(p), p]));
  let dirty = false;
  Object.keys(pendingEdits).forEach(key => {
    const e = pendingEdits[key], p = byKey.get(key);
    const confirmed = !p || (!e.patch.delete && Object.entries(e.patch).every(([k, v]) => k === 'ru_pick' ? !!p.ru_pick === !!v : p[k] === v));
    if (confirmed || Date.now() - e.t > EDIT_PENDING_TTL_MS) { delete pendingEdits[key]; dirty = true; return; }
    applyPatchLocally(p, e.patch);
  });
  if (dirty) savePending();
}

async function flushEdits(keepalive) {
  clearTimeout(flushTimer); flushTimer = null;
  const unsent = Object.entries(pendingEdits).filter(([, e]) => !e.sent);
  if (!unsent.length) return;
  const token = getToken();
  if (!token) { showToast('Save your GitHub token (＋ Add paper) so changes can be sent.', 'error', 10000); return; }
  for (let i = 0; i < unsent.length; i += EDIT_BATCH) {
    const chunk = unsent.slice(i, i + EDIT_BATCH);
    const stamps = chunk.map(([key, e]) => [key, e.t]);
    const edits = chunk.map(([key, e]) => Object.assign({ key }, e.patch));
    try {
      const resp = await fetch(EDIT_WORKFLOW_URL, {
        method: 'POST', keepalive: !!keepalive, headers: ghHeaders(token),
        body: JSON.stringify({ ref: 'main', inputs: { edits: JSON.stringify(edits) } }),
      });
      if (resp.status === 204) {
        stamps.forEach(([key, t]) => { if (pendingEdits[key] && pendingEdits[key].t === t) pendingEdits[key].sent = true; });
        savePending();
        showToast('Changes sent — the site updates in about a minute.', 'success', 6000);
      } else {
        let msg;
        if (resp.status === 401) msg = 'Invalid token — update it via "Change token" in the ＋ Add Paper window.';
        else if (resp.status === 403) msg = 'Token lacks Actions permission — enable Actions (R&W) on your token.';
        else if (resp.status === 404 || resp.status === 422) msg = 'The "Edit Papers" workflow was not found on main — it may not be deployed yet.';
        else msg = 'Could not send changes (GitHub error ' + resp.status + '). They stay on this page and will retry on your next edit.';
        showToast(msg, 'error', 12000);
        return;
      }
    } catch (err) {
      showToast('Could not send changes: ' + err.message + '. They will retry on your next edit.', 'error', 12000);
      return;
    }
  }
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flushEdits(true); });

/* ── Gear menu interaction ──────────────────────────────────────────────── */
function closeGears(except) { document.querySelectorAll('.card-gear.open').forEach(g => { if (g !== except) g.classList.remove('open'); }); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeGears(); });

grid.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (!el || el.tagName === 'INPUT') return;
  const card = el.closest('.card');
  const p = card && PAPER_BY_KEY.get(card.dataset.key);
  if (!p) return;
  const act = el.dataset.act;
  if (act === 'gear') {
    const g = el.closest('.card-gear');
    const open = !g.classList.contains('open');
    closeGears(); g.classList.toggle('open', open);
    if (open) {   // scroll just enough to keep the menu clear of the sticky header/filter bar
      const r = g.querySelector('.gear-panel').getBoundingClientRect();
      const top = filtersEl.getBoundingClientRect().bottom + 12;
      if (r.top < top) window.scrollBy(0, r.top - top);
      else if (r.bottom > window.innerHeight - 12) window.scrollBy(0, r.bottom - window.innerHeight + 12);
    }
  } else if (act === 'save-link') {
    const status = card.querySelector('.gear-status');
    const u = safeUrl(card.querySelector('.gear-input').value);
    if (!u) { status.textContent = 'Enter a full https:// link.'; return; }
    queueEdit(p, { pdf_link: u });
    showToast(isDirectPdf(u) ? 'PDF link saved.' : 'Link saved — it doesn\'t look like a direct PDF file, so the card will say "Full text".', 'success', 8000);
  } else if (act === 'clear-link') {
    queueEdit(p, { pdf_link: '' });
    showToast('PDF link removed.', 'success', 5000);
  } else if (act === 'delete') {
    if (!window.confirm('Remove "' + (p.title || 'this paper').slice(0, 120) + '" from the list?\n\nThe agent won\'t add it back.')) return;
    queueEdit(p, { delete: true });
    showToast('Removed — the site updates in about a minute.', 'success', 6000);
  }
});
grid.addEventListener('change', e => {
  if (!e.target.dataset || e.target.dataset.act !== 'ru-pick') return;
  const card = e.target.closest('.card');
  const p = card && PAPER_BY_KEY.get(card.dataset.key);
  if (p) queueEdit(p, { ru_pick: e.target.checked });
});


/* ── Notes + PDF upload interaction ───────────────────────────────────────── */
document.getElementById('grid').addEventListener('change', e => {
  const input = e.target.closest('.pdf-file-input');
  if (!input) return;
  const file = input.files[0];
  const popover = input.closest('[data-pdfbox]');
  if (!popover) return;
  const nameEl = popover.querySelector('.pdf-selected-name');
  const status = popover.querySelector('.pdf-upload-status');
  if (nameEl) nameEl.textContent = file ? file.name : '';
  if (status) { status.textContent = file ? 'Ready to upload.' : ''; status.style.color = ''; }
});

const PDF_API = 'https://api.github.com/repos/ismi-ops/literature-rg/contents/pdfs/';
function ghHeaders(token) {
  return { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json' };
}
function putPdf(slug, token, b64, sha) {
  const body = { message: sha ? 'chore: replace PDF via site' : 'chore: upload PDF via site', content: b64 };
  if (sha) body.sha = sha;
  return fetch(PDF_API + encodeURIComponent(slug), { method: 'PUT', headers: ghHeaders(token), body: JSON.stringify(body) });
}

async function handlePdfUpload(btn, event) {
  event.stopPropagation();
  const popover = btn.closest('[data-pdfbox]');
  const status = popover ? popover.querySelector('.pdf-upload-status') : null;
  const fileInput = popover ? popover.querySelector('.pdf-file-input') : null;
  const file = fileInput && fileInput.files[0];
  if (!file) {
    if (status) { status.textContent = 'Please choose a PDF file first.'; status.style.color = '#b91c1c'; }
    return;
  }
  const card = btn.closest('.card');
  const slug = card ? card.dataset.pdfslug : null;
  if (!slug) return;
  const closeMenus = () => {
    const a = btn.closest('.btn-add-pdf'); if (a) a.classList.remove('open');
    const g = btn.closest('.card-gear'); if (g) g.classList.remove('open');
  };
  const token = getToken();
  if (!token) {
    closeMenus();
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
      let resp = await putPdf(slug, token, b64, null);
      if (resp.status === 422) {   // a file with this name exists (replacing a PDF): GitHub wants its sha
        const cur = await fetch(PDF_API + encodeURIComponent(slug), { headers: ghHeaders(token) });
        const meta = cur.ok ? await cur.json().catch(() => ({})) : {};
        if (meta.sha) resp = await putPdf(slug, token, b64, meta.sha);
      }
      if (resp.ok) {
        if (status) { status.textContent = '✓ Uploaded!'; status.style.color = '#16a34a'; }
        closeMenus();
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
document.addEventListener('click', e => {
  document.querySelectorAll('.btn-add-pdf.open').forEach(b => b.classList.remove('open'));
  if (!e.target.closest('.card-gear')) closeGears();
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
  document.getElementById('filters-clear').hidden = n === 0;
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
  applyPendingEdits();
  PAPER_BY_KEY = new Map(PAPERS.map(p => [paperKey(p), p]));
  computeTopPicks(PAPERS);
  dataReady = true;
  update();
  if (getToken() && Object.values(pendingEdits).some(e => !e.sent)) scheduleFlush();
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
  syncAdminFilters();
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
