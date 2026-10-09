"""Markdown rendering and file-kind detection. Safe to import without GTK."""

from __future__ import annotations

import re
from pathlib import Path

import cmarkgfm

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

_SRC_RE = re.compile(r"""src=(["'])([^"']+)\1""")
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in MARKDOWN_SUFFIXES:
        return "markdown"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "other"


def markdown_fragment(text: str) -> str:
    """Return GitHub-flavored HTML for *text*. Raw HTML in the source is escaped."""
    return cmarkgfm.github_flavored_markdown_to_html(text)


def render_document(text: str, base_dir: Path) -> str:
    fragment = _rewrite_local_images(markdown_fragment(text), base_dir)
    css = (_DATA_DIR / "preview.css").read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<style>{css}</style></head><body>{fragment}</body></html>"
    )


def _rewrite_local_images(html: str, base_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        quote, src = match.group(1), match.group(2)
        if "://" in src or src.startswith("data:"):
            return match.group(0)
        return f"src={quote}{(base_dir / src).resolve().as_uri()}{quote}"

    return _SRC_RE.sub(replace, html)
