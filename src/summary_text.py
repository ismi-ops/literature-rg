"""Tidy summary text taken from paper abstracts."""
import re

_HEADING = re.compile(
    r"^\s*(abstract|summary|background|introduction|objectives?|purpose|aims?|context|rationale|importance|motivation)\b[ \t]*([:.–—-]*)[ \t]*",
    re.I,
)


def clean_summary(text: str) -> str:
    """Drop a leading section heading ("BACKGROUND", "Summary:", "Abstract") and stray line breaks.

    A heading is only removed when it is clearly a heading: followed by punctuation or a line break,
    written in capitals, or followed by a capitalised word. "Summary statistics from ..." and
    "Background noise reduces ..." are real sentences and stay as they are.
    """
    text = (text or "").replace("\xa0", " ").strip()
    for _ in range(2):   # "ABSTRACT Background ..." carries two headings
        m = _HEADING.match(text)
        if not m:
            break
        word, punct, rest = m.group(1), m.group(2), text[m.end():]
        broke_line = "\n" in text[: m.end() + 1]
        is_heading = bool(punct) or broke_line or word.isupper() or rest[:1].isupper() or rest[:1].isdigit()
        if not is_heading or not rest:
            break
        text = rest
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:] if text else text


def summarize_abstract(abstract: str, max_sentences: int = 3, max_words: int = 90) -> str:
    """The opening sentences of an abstract, without its heading, kept to a readable length."""
    sentences = re.split(r"(?<=[.!?])\s+", clean_summary(abstract))
    out, words = [], 0
    for s in sentences:
        if out and (len(out) >= max_sentences or words + len(s.split()) > max_words):
            break
        out.append(s)
        words += len(s.split())
    return " ".join(out)
