"""Plan, apply and undo. Nothing is overwritten, deleted or moved out of the tidied folder's tree."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from . import classify as C
from .reader import open_untouched
from .config import LEAVE, Config

PLAN = ".sloth-plan.json"
LEDGER = ".sloth-ledger.jsonl"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open_untouched(path) as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def last_touched(st: os.stat_result) -> float:
    """The later of 'last modified' and 'last opened'. Forgotten means neither has happened for a while."""
    return max(st.st_mtime, st.st_atime)


def candidates(root: Path, cfg: Config, now: float | None = None) -> tuple[list[Path], list[tuple[str, str]]]:
    """Split a folder into files sloth may tidy and files it must leave alone (with the reason, for the plan page)."""
    now = now or time.time()
    take, skip = [], []
    for p in sorted(root.iterdir()):
        if p.name.startswith(".") or p.name.startswith("desktop.ini"):
            continue
        if p.is_symlink():
            skip.append((p.name, "symlink")); continue
        if not p.is_file():
            continue
        days = (now - last_touched(p.stat())) / 86400
        if days < cfg.ignored_for_days:
            skip.append((p.name, f"touched {days:.1f} days ago, less than {cfg.ignored_for_days:g}: you may still be using it")); continue
        take.append(p)
    return take, skip


def make_plan(root: Path, cfg: Config, *, pace: float = 0.0, url: str | None = None, log=print) -> dict:
    files, skipped = candidates(root, cfg)
    for name, why in skipped:
        log(f"left alone {name}: {why}")
    rows = []
    for i, p in enumerate(files, 1):
        res = C.classify(cfg, p, **({"url": url} if url else {}))
        st = p.stat()
        rows.append({"file": p.name, "size": st.st_size, "mtime": st.st_mtime, **res})
        log(f"[{i}/{len(files)}] {p.name} -> {res['folder']} ({res['confidence']}, {res['seconds']}s) {res['reason']}")
        if pace and i < len(files):
            time.sleep(pace)  # the sloth rests
    plan = {"root": str(root), "created": time.time(), "rows": rows, "skipped": skipped}
    (root / PLAN).write_text(json.dumps(plan, indent=1))
    return plan


def _free(dest: Path) -> Path:
    if not dest.exists():
        return dest
    n = 1
    while True:
        cand = dest.with_name(f"{dest.stem}-{n}{dest.suffix}")
        if not cand.exists():
            return cand
        n += 1


def apply_plan(root: Path, cfg: Config, log=print) -> dict:
    plan = json.loads((root / PLAN).read_text())
    moved = refused = 0
    for r in plan["rows"]:
        if r["folder"] == LEAVE:
            continue
        src = root / r["file"]
        if r["folder"] not in cfg.names:
            refused += 1; log(f"refuse {r['file']}: folder {r['folder']!r} not in config"); continue
        if not src.is_file() or src.is_symlink():
            refused += 1; log(f"refuse {r['file']}: gone or a symlink"); continue
        st = src.stat()
        if st.st_size != r["size"] or abs(st.st_mtime - r["mtime"]) > 1:
            refused += 1; log(f"refuse {r['file']}: changed since the plan was made"); continue
        d = root / r["folder"]; d.mkdir(exist_ok=True)
        dest = _free(d / src.name)
        digest = sha(src)
        shutil.move(str(src), str(dest))
        with open(root / LEDGER, "a") as fh:
            fh.write(json.dumps({"t": time.time(), "from": str(src.relative_to(root)), "to": str(dest.relative_to(root)), "sha256": digest}) + "\n")
        moved += 1; log(f"moved {src.name} -> {r['folder']}/")
    return {"moved": moved, "refused": refused}


def undo(root: Path, log=print) -> dict:
    led = root / LEDGER
    if not led.exists():
        return {"restored": 0, "refused": 0}
    entries = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
    restored = refused = 0
    for e in reversed(entries):
        src, dst = root / e["to"], root / e["from"]
        if not src.is_file() or dst.exists() or sha(src) != e["sha256"]:
            refused += 1; log(f"refuse undo {e['to']}: missing, target taken, or content changed"); continue
        shutil.move(str(src), str(dst)); restored += 1; log(f"restored {e['from']}")
    for d in {(root / e["to"]).parent for e in entries}:
        try:
            d.rmdir()
        except OSError:
            pass
    if not refused:
        led.rename(root / (LEDGER + f".undone-{int(time.time())}"))
    return {"restored": restored, "refused": refused}
