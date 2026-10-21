"""Turn a file into a short text snippet the model can read. Never reads more than a few KB."""
from __future__ import annotations

import os
from pathlib import Path

TEXT_EXT = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".eml", ".log", ".py", ".js", ".yaml", ".yml",
            ".toml", ".ics", ".sql", ".tsv", ".srt", ".xml", ".tex", ".sh", ".bak", ".rst", ".ini", ".cfg"}


def open_untouched(path: Path, mode: str = "rb"):
    """Open for reading WITHOUT bumping the file's access time. sloth-sort's whole rule is 'leave files I have not opened
    for a week alone'; if reading a file counted as opening it, one plan would make every file look fresh."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
    except PermissionError:  # O_NOATIME is only allowed on files you own
        fd = os.open(path, os.O_RDONLY)
    return os.fdopen(fd, mode)


def snippet(path: Path, limit: int = 1200) -> tuple[str, str]:
    """Return (kind, text). kind is 'text', 'pdf' or 'binary' (name and size only)."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            with open_untouched(path) as fh:
                r = PdfReader(fh)
                return _pdf_text(r, limit)
        except Exception:
            pass
        return "binary", ""
    if ext in TEXT_EXT or ext == "":
        try:
            with open_untouched(path) as fh:
                raw = fh.read(limit * 4)
            if b"\x00" in raw:
                return "binary", ""
            return "text", raw.decode("utf-8", errors="replace")[:limit].strip()
        except OSError:
            return "binary", ""
    return "binary", ""


def _pdf_text(r, limit):
    out = ""
    for page in r.pages[:3]:
        out += (page.extract_text() or "") + "\n"
        if len(out) >= limit:
            break
    if out.strip():
        return "pdf", " ".join(out.split())[:limit]
    return "binary", ""
