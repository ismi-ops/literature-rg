"""Formatting rules for paper titles, shared by ingestion and the title audit."""
import html
import re

_TAG = re.compile(r"</?(?:i|b|em|strong|sub|sup|u|scp|jats:[a-z-]+|mml:[a-z-]+)\b[^>]*>", re.I)


def clean_title(title: str) -> str:
    """Strip markup/entities and stray whitespace, and drop a single trailing full stop
    (PubMed-style titles end with one; Crossref/bioRxiv ones don't — the site shows them without)."""
    t = html.unescape(title or "")
    t = _TAG.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    if t.endswith(".") and not t.endswith(".."):
        t = t[:-1].rstrip()
    return t


def norm(title: str) -> str:
    """Comparison key: lowercase letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", clean_title(title).lower())
