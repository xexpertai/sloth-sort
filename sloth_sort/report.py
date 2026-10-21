"""Write a plain HTML page of a plan, so the morning-after review is one look instead of a terminal scroll."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .mover import PLAN


def _tidy(reason: str) -> str:
    """The model sometimes runs out of tokens mid-sentence; show up to the last whole word and mark the cut."""
    r = reason.strip()
    if r and r[-1] not in ".!?)'\"`":
        r = r.rsplit(" ", 1)[0].rstrip(",;:") + " ..."
    return r


def write_report(root: Path, out: Path | None = None) -> Path:
    plan = json.loads((root / PLAN).read_text())
    rows = plan["rows"]
    moves = [r for r in rows if r["folder"] != "leave"]
    css = ("body{font:16px/1.5 system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#1d2330}"
           "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.45rem .6rem;border-bottom:1px solid #d9dde5;vertical-align:top}"
           "th{background:#f1f3f7}.leave{color:#6a7385}.high{color:#14663a;font-weight:600}.medium{color:#8a5a00}.low{color:#a02a2a}"
           "code{background:#f1f3f7;padding:.1rem .3rem;border-radius:4px}")
    body = [f"<h1>Sloth plan</h1><p>{len(moves)} of {len(rows)} files would move. {len(plan['skipped'])} left alone because you touched them lately. "
            f"Nothing has been touched yet: run <code>sloth apply</code>, or <code>sloth undo</code> afterwards.</p>",
            "<table><tr><th>File</th><th>Goes to</th><th>Sure?</th><th>Why (model's words)</th></tr>"]
    for r in rows:
        cls = "leave" if r["folder"] == "leave" else ""
        body.append(f"<tr class='{cls}'><td>{html.escape(r['file'])}</td><td>{html.escape(r['folder'] if r['folder']!='leave' else 'stays put')}</td>"
                    f"<td class='{r['confidence']}'>{r['confidence']}</td><td>{html.escape(_tidy(r['reason']))}</td></tr>")
    for name, why in plan["skipped"]:
        body.append(f"<tr class='leave'><td>{html.escape(name)}</td><td>not looked at</td><td></td><td>{html.escape(why)}</td></tr>")
    body.append("</table>")
    out = out or (root / "sloth-plan.html")
    out.write_text(f"<!doctype html><meta charset=utf-8><title>Sloth plan</title><style>{css}</style>" + "".join(body))
    return out
