"""Generate the static site from papers.json.

Outputs (all served as-is by GitHub Pages):
  index.html       page shell + inline password gate
  filters.json     filter options + totals (small; fetched first so the filter UI builds immediately)
  papers_data.json every paper (fetched alongside, renders cards and drives live filter counts)
app.js is hand-written and committed as-is; only its content hash is read here for cache-busting.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from src.people_of_interest import load_people

PAPERS_PATH = Path("papers.json")
INDEX_PATH = Path("index.html")
APP_JS_PATH = Path("app.js")
FILTERS_PATH = Path("filters.json")
DATA_PATH = Path("papers_data.json")

TAG_BLOCKLIST = ["perspective", "perspectives", "review", "research", "preprint", "editorial", "comment", "letter"]
TYPES = ["all", "research", "review", "perspective", "article"]


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def sort_papers(papers):
    """Newest added first, then highest score (stable for ties)."""
    return sorted(papers, key=lambda p: (p.get("added") or "", p.get("score") or 0), reverse=True)


def build_filters(papers):
    topic_tags = Counter(
        t for p in papers for t in (p.get("tags") or []) if t.lower() not in TAG_BLOCKLIST
    )
    years = Counter(str(p["year"]).strip() for p in papers if str(p.get("year") or "").strip())
    authors = Counter(p["vip_author"] for p in papers if p.get("vip_author"))
    type_counts = Counter(p.get("type") or "research" for p in papers)
    type_counts["all"] = len(papers)
    return {
        "total": len(papers),
        "types": TYPES,
        "typeCounts": {t: type_counts.get(t, 0) for t in TYPES},
        "hasPreprint": any(p.get("preprint") for p in papers),
        "tagBlocklist": TAG_BLOCKLIST,
        "people": load_people(),   # always shown in collapsed author lists
        "tags": [{"name": t, "count": n} for t, n in topic_tags.most_common()],
        "years": [{"name": y, "count": years[y]} for y in sorted(years, key=lambda y: (not y.isdigit(), -int(y) if y.isdigit() else 0, y))],
        "authors": [{"name": a, "count": authors[a]} for a in sorted(authors, key=lambda a: (a.split()[-1].lower(), a.lower()))],
    }


def _version(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:10]


def build_index(app_js: bytes, filters_json: str, data_json: str) -> str:
    return (
        HTML_TEMPLATE
        .replace("__APP_V__", _version(app_js))
        .replace("__FILTERS_V__", _version(filters_json.encode("utf-8")))
        .replace("__DATA_V__", _version(data_json.encode("utf-8")))
    )


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ru's Repository · Cell Science</title>
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
  .filters-top { max-width: 1100px; margin: auto; display: flex; align-items: center; gap: 12px; }
  .filters-top + .filters-inner { margin: 8px auto 0; }
  .filters-inner { max-width: 1100px; }
  .filters.collapsed .filters-inner { display: none; }
  .filters-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 2px 4px; border: none; background: none; color: var(--text); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; cursor: pointer; }
  .filters-toggle:hover { color: var(--accent); }
  .ft-caret { display: inline-block; transition: transform .15s; }
  .filters.collapsed .ft-caret { transform: rotate(-90deg); }
  .ft-badge { font-size: 11px; font-weight: 600; text-transform: none; letter-spacing: 0; padding: 1px 8px; border-radius: 10px; background: var(--accent); color: #fff; }
  .ft-badge:empty { display: none; }
  .filters-clear { padding: 2px 10px; border-radius: 12px; border: 1px solid var(--border); background: none; color: var(--muted); font-size: 12px; cursor: pointer; transition: border-color .12s, color .12s; }
  .filters-clear:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Multiselect dropdowns ────────────────────────────────────────────── */
  .filter-bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .dd { position: relative; }
  .dd.is-empty { display: none; }
  .dd-btn { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 13px; cursor: pointer; transition: border-color .12s, background .12s; }
  .dd-btn:hover, .dd.open .dd-btn { border-color: var(--accent); }
  .dd-btn.has-sel { background: var(--accent-light); border-color: var(--accent); color: var(--accent); font-weight: 600; }
  .dd-n { min-width: 18px; padding: 0 6px; border-radius: 9px; background: var(--accent); color: #fff; font-size: 11px; font-weight: 600; line-height: 18px; text-align: center; }
  .dd-n:empty { display: none; }
  .dd-caret { font-size: 11px; opacity: .7; transition: transform .15s; }
  .dd.open .dd-caret { transform: rotate(180deg); }
  .dd-panel { display: none; position: absolute; top: calc(100% + 6px); left: 0; z-index: 150; min-width: 220px; max-width: min(340px, calc(100vw - 32px)); max-height: 340px; overflow-y: auto; padding: 6px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.18); }
  .dd.open .dd-panel { display: block; }
  .dd.align-right .dd-panel { left: auto; right: 0; }
  .dd-opt { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; font-size: 13px; cursor: pointer; user-select: none; }
  .dd-opt:hover { background: var(--accent-light); }
  .dd-opt input { width: 15px; height: 15px; flex-shrink: 0; accent-color: var(--accent); cursor: pointer; }
  .dd-label { flex: 1; }
  .dd-opt .count { font-size: 11.5px; color: var(--muted); }
  .dd-opt.checked .dd-label { font-weight: 600; }
  .dd-opt.zero:not(.checked) { opacity: .4; }

  /* ── Toolbar + pagination ─────────────────────────────────────────────── */
  .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; font-size: 13px; color: var(--muted); }
  .page-size-label { display: inline-flex; align-items: center; gap: 6px; }
  #page-size { padding: 4px 8px; border: 1px solid var(--border); border-radius: 7px; background: var(--surface); color: var(--text); font-size: 13px; cursor: pointer; }
  .pager { display: flex; justify-content: center; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 28px; }
  .page-btn { min-width: 34px; padding: 5px 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 13px; cursor: pointer; transition: border-color .12s, color .12s; }
  .page-btn:hover:not(:disabled):not(.active) { border-color: var(--accent); color: var(--accent); }
  .page-btn.active { background: var(--chip-active-bg); color: var(--chip-active-text); border-color: var(--chip-active-bg); cursor: default; }
  .page-btn:disabled { opacity: .4; cursor: default; }
  .page-gap { color: var(--muted); padding: 0 2px; }

  /* ── Cards ────────────────────────────────────────────────────────────── */
  main { max-width: 1100px; margin: 24px auto; padding: 0 24px 48px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .card { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 10px; transition: box-shadow .15s; }
  .card:hover { box-shadow: var(--shadow-hover); }
  .card-corner { position: absolute; bottom: 10px; right: 12px; display: flex; align-items: center; gap: 8px; }
  .top-pick-star { font-size: 20px; line-height: 1; user-select: none; cursor: default; filter: drop-shadow(0 1px 2px rgba(0,0,0,.15)); }
  .card-gear { position: relative; }
  .gear-btn { background: none; border: none; font-size: 19px; line-height: 1; color: var(--muted); cursor: pointer; padding: 2px 4px; border-radius: 6px; opacity: .55; transition: opacity .12s, color .12s; }
  .gear-btn:hover, .card-gear.open .gear-btn { opacity: 1; color: var(--accent); }
  .gear-panel { display: none; position: absolute; bottom: calc(100% + 8px); right: 0; z-index: 200; width: 290px; max-width: calc(100vw - 48px); background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; box-shadow: 0 4px 20px rgba(0,0,0,.22); text-align: left; cursor: default; }
  .card-gear.open .gear-panel { display: flex; flex-direction: column; gap: 10px; }
  .gear-check { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; cursor: pointer; user-select: none; }
  .gear-check input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
  .gear-section { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--border); padding-top: 10px; }
  .gear-h { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
  .gear-current { font-size: 12px; color: var(--muted); word-break: break-all; }
  .gear-current a { color: var(--accent); }
  .gear-input { width: 100%; padding: 6px 8px; border: 1px solid var(--border); border-radius: 7px; background: var(--bg); color: var(--text); font-size: 12.5px; outline: none; }
  .gear-input:focus { border-color: var(--accent); }
  .gear-row { display: flex; gap: 6px; }
  .gear-btn2 { flex: 1; padding: 6px 8px; border-radius: 7px; border: none; background: var(--accent); color: #fff; font-size: 12.5px; font-weight: 600; cursor: pointer; }
  .gear-btn2.ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); font-weight: 500; }
  .gear-btn2:hover { opacity: .88; }
  .gear-status { font-size: 11.5px; color: #b91c1c; min-height: 0; }
  .gear-or { font-size: 11.5px; color: var(--muted); margin-top: 4px; }
  .gear-delete { padding: 6px 8px; border-radius: 7px; border: 1px solid #fca5a5; background: transparent; color: #b91c1c; font-size: 12.5px; cursor: pointer; text-align: left; }
  .gear-delete:hover { background: #fee2e2; }
  @media (prefers-color-scheme: dark) { .gear-delete { color: #fca5a5; border-color: #7f1d1d; } .gear-delete:hover { background: #450a0a; } .gear-status { color: #fca5a5; } }
  .card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; }
  .badge-research { background: #edeaff; color: #6464FF; }
  .badge-review { background: #fde8f0; color: #CD0F55; }
  .badge-perspective { background: #e0faf9; color: #007d75; }
  .badge-article { background: #fef6d9; color: #DE9C00; }
  .badge-preprint { background: #f3fad0; color: #6a7a04; }
  .badge-published { background: #dcfce7; color: #15803d; }
  .badge-collab { background: #fff0e8; color: #b05000; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
  @media (prefers-color-scheme: dark) {
    .badge-research { background: #1a1a3d; color: #a0a0ff; }
    .badge-review { background: #3b0018; color: #ff80aa; }
    .badge-perspective { background: #003630; color: #4dd9d3; }
    .badge-article { background: #2a1f00; color: #DE9C00; }
    .badge-preprint { background: #1e2500; color: #CCE805; }
    .badge-published { background: #052e16; color: #86efac; }
    .badge-collab { background: #2a1400; color: #ff9955; }
    .card-relevance { border-color: #00A59B; background: transparent; }
    .card-relevance-label { color: #4dd9d3; }
    .card-relevance-text { color: var(--text); opacity: .88; }
    .tag { background: transparent; color: #a0a0ff; border-color: #a0a0ff; }
    .btn-pdf { background: #ff80aa; color: #fff; border-color: #ff80aa; }
  }
  .card-date { font-size: 11.5px; color: var(--muted); margin-left: auto; }
  .card-title { font-size: 15px; font-weight: 650; line-height: 1.4; }
  .card-title a { color: var(--text); text-decoration: none; }
  .card-title a:hover { color: var(--accent); text-decoration: underline; }
  .card-authors { font-size: 13px; color: var(--muted); line-height: 1.6; }
  .author-link { color: var(--muted); text-decoration: none; }
  .au-sep { color: var(--border); }
  .au-full { display: none; }
  .card-authors.expanded .au-short { display: none; }
  .card-authors.expanded .au-full { display: inline; }
  .au-toggle { padding: 0 8px; border-radius: 10px; border: 1px solid var(--border); background: none; color: var(--muted); font-size: 11.5px; cursor: pointer; white-space: nowrap; transition: border-color .12s, color .12s; }
  .au-toggle:hover { border-color: var(--accent); color: var(--accent); }
  .author-link:hover { color: var(--accent); text-decoration: underline; }
  .card-venue { font-size: 12.5px; color: var(--muted); font-style: italic; }
  .journal-link { color: inherit; text-decoration: none; }
  .journal-link:hover { text-decoration: underline; }
  .card-summary { font-size: 13.5px; color: var(--text); opacity: .88; }
  .card-relevance { margin-top: 10px; border-left: 3px solid #00A59B; border-radius: 4px; background: transparent; padding: 8px 12px; }
  .card-relevance-label { font-size: 10.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #007d75; opacity: .9; margin-bottom: 3px; }
  .card-relevance-text { font-size: 13px; color: var(--text); font-style: italic; line-height: 1.45; opacity: .88; }
  .card-tags { display: flex; flex-wrap: wrap; gap: 5px; }
  .tag { font-size: 11.5px; padding: 2px 8px; border-radius: 10px; background: transparent; color: #6464FF; border: 1px solid #6464FF; cursor: pointer; }
  .tag:hover { opacity: .8; }
  .card-actions { display: flex; gap: 8px; margin-top: 2px; align-items: center; }
  .btn-pdf { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 7px; background: #CD0F55; color: #fff; text-decoration: none; border: 1px solid #CD0F55; transition: opacity .12s; }
  .btn-pdf:hover { opacity: .85; }
  .btn-fulltext { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; padding: 4px 10px; border-radius: 7px; color: var(--muted); text-decoration: none; border: 1px solid var(--border); transition: border-color .12s, color .12s; }
  .btn-fulltext:hover { border-color: var(--accent); color: var(--accent); }
  .btn-add-pdf { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; padding: 4px 10px; border-radius: 7px; background: transparent; color: var(--muted); border: 1px dashed var(--muted); cursor: pointer; opacity: .6; transition: opacity .12s; position: relative; user-select: none; }
  .btn-add-pdf:hover { opacity: 1; }
  .pdf-popover { display: none; position: absolute; bottom: calc(100% + 8px); left: 0; z-index: 200; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; width: 290px; box-shadow: 0 4px 20px rgba(0,0,0,.22); text-align: left; cursor: default; }
  .btn-add-pdf.open .pdf-popover { display: block; }
  .pdf-popover-title { font-size: 12px; font-weight: 700; color: var(--text); margin-bottom: 10px; }
  .pdf-file-input { display: none; }
  .pdf-file-label { display: inline-flex; align-items: center; gap: 5px; padding: 5px 12px; border-radius: 7px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 12px; cursor: pointer; transition: border-color .12s, color .12s; }
  .pdf-file-label:hover { border-color: var(--accent); color: var(--accent); }
  .pdf-selected-name { font-size: 11px; font-family: monospace; color: var(--muted); margin: 6px 0 8px; min-height: 14px; word-break: break-all; }
  .pdf-upload-btn { display: block; width: 100%; padding: 7px; border-radius: 7px; border: none; background: var(--accent); color: #fff; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity .12s; }
  .pdf-upload-btn:disabled { opacity: .35; cursor: default; }
  .pdf-upload-btn:not(:disabled):hover { opacity: .85; }
  .pdf-upload-status { font-size: 11.5px; margin-top: 7px; color: var(--muted); min-height: 14px; line-height: 1.4; }
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
  /* ── Toast notifications ──────────────────────────────────────────────── */
  #toast-container { position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
  .toast { pointer-events: auto; display: flex; align-items: flex-start; gap: 10px; padding: 12px 16px; border-radius: 10px; font-size: 13px; line-height: 1.4; max-width: 320px; box-shadow: 0 4px 20px rgba(0,0,0,.22); animation: toast-in .2s ease; }
  .toast.success { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
  .toast.error   { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
  @media (prefers-color-scheme: dark) {
    .toast.success { background: #14532d; color: #86efac; border-color: #166534; }
    .toast.error   { background: #450a0a; color: #fca5a5; border-color: #7f1d1d; }
  }
  .toast-close { background: none; border: none; font-size: 16px; cursor: pointer; color: inherit; opacity: .6; padding: 0; line-height: 1; flex-shrink: 0; }
  .toast-close:hover { opacity: 1; }
  @keyframes toast-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

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
  .modal-optional { font-weight: 400; color: var(--muted); font-size: 12px; }
  .modal-label-gap { margin-top: 14px; }
  .modal-pdf-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 6px 0 14px; }
  .modal-pdf-row .pdf-selected-name { margin: 0; min-height: 0; }
  .modal-token-row { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
  .modal-token-btn { background: none; border: none; color: var(--accent); font-size: 12px; cursor: pointer; padding: 0; text-decoration: underline; }
  .modal-check-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text); cursor: pointer; user-select: none; }
  .modal-check-row input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; flex-shrink: 0; }
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
    <h2>Ru's Repository</h2>
    <p>Enter the password to continue.</p>
    <input id="pw-input" type="password" placeholder="Password" autocomplete="current-password">
    <div id="pw-error"></div>
    <button id="pw-btn">Unlock</button>
  </div>
</div>

<header>
  <div class="header-inner">
    <div class="header-title">Ru's Repository <span>· Cell Science</span></div>
    <input id="search" type="search" placeholder="Search title, author, journal…" autocomplete="off">
    <div id="result-count"></div>
    <button class="btn-add" id="btn-add-paper">+ Add paper</button>
  </div>
</header>
<div class="filters">
  <div class="filters-top">
    <button type="button" class="filters-toggle" id="filters-toggle" aria-expanded="true" aria-controls="filters-inner"><span class="ft-caret">&#9662;</span> Filters <span class="ft-badge" id="filters-badge"></span></button>
    <button type="button" class="filters-clear" id="filters-clear" hidden>Clear all</button>
  </div>
  <div class="filters-inner" id="filters-inner">
    <div class="filter-bar" id="filter-bar"></div>
  </div>
</div>
<main>
  <div class="toolbar">
    <span id="range-label"></span>
    <label class="page-size-label">Per page <select id="page-size"></select></label>
  </div>
  <div class="grid" id="grid"><div class="empty">Loading papers&hellip;</div></div>
  <nav class="pager" id="pager" aria-label="Pagination"></nav>
</main>

<div id="toast-container"></div>
<!-- Add Paper modal -->
<div class="modal-backdrop" id="add-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title-text">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title" id="modal-title-text">Add Paper</span>
      <button class="modal-close" id="modal-close" aria-label="Close">&times;</button>
    </div>

    <!-- Screen 1: GitHub token setup -->
    <div id="modal-token-screen">
      <p class="modal-desc">To add papers and upload PDFs you need a GitHub Personal Access Token (PAT) stored only in your browser.</p>
      <p class="modal-desc"><strong>Fine-grained PAT:</strong> enable <em>Actions</em>, <em>Contents</em>, and <em>Workflows</em> permissions (read &amp; write) for <code>ismi-ops/literature-rg</code>.</p>
      <p class="modal-desc"><a class="modal-link" href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">Create a fine-grained token on GitHub →</a></p>
      <div class="modal-label">Personal Access Token</div>
      <input class="modal-input" id="token-input" type="password" placeholder="ghp_…" autocomplete="off">
      <button class="modal-btn" id="token-save-btn">Save &amp; continue</button>
      <div class="modal-feedback" id="token-feedback"></div>
    </div>

    <!-- Screen 2: Paper URL / DOI input -->
    <div id="modal-paper-screen" style="display:none">
      <div class="modal-label">Paper URL or DOI</div>
      <p class="modal-desc">Paste a link (Nature, bioRxiv, PubMed…) or a DOI like <code>10.1038/…</code>. The authors, summary and relevance note are filled in automatically — check back in ~2 minutes.</p>
      <input class="modal-input" id="paper-input" type="text" placeholder="https://… or 10.xxxx/…" autocomplete="off">
      <div class="modal-label modal-label-gap">PDF <span class="modal-optional">(optional — attach it now to do both in one step)</span></div>
      <div class="modal-pdf-row">
        <label class="pdf-file-label"><input type="file" accept=".pdf,application/pdf" id="paper-pdf-input" class="pdf-file-input">&#128194; Choose PDF…</label>
        <span class="pdf-selected-name" id="paper-pdf-name"></span>
        <button type="button" class="modal-token-btn" id="paper-pdf-clear" hidden>Remove</button>
      </div>
      <label class="modal-check-row">
        <input type="checkbox" id="ru-pick-check">
        Ru's Picks
      </label>
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
</script>
<script src="app.js?v=__APP_V__" data-filters="filters.json?v=__FILTERS_V__" data-papers="papers_data.json?v=__DATA_V__" defer></script>
</body>
</html>"""


def main():
    if not PAPERS_PATH.exists():
        print("papers.json not found")
        return
    if not APP_JS_PATH.exists():
        print("app.js not found")
        return
    with open(PAPERS_PATH) as f:
        papers = json.load(f)
    papers = sort_papers([p for p in papers if not p.get("rejected")])
    filters_json = _dumps(build_filters(papers))
    data_json = _dumps(papers)
    FILTERS_PATH.write_text(filters_json, encoding="utf-8")
    DATA_PATH.write_text(data_json, encoding="utf-8")
    INDEX_PATH.write_text(build_index(APP_JS_PATH.read_bytes(), filters_json, data_json), encoding="utf-8")
    print(f"Generated {INDEX_PATH}, {FILTERS_PATH}, {DATA_PATH} ({len(papers)} papers)")


if __name__ == "__main__":
    main()
