"""sloth plan|apply|undo|status. Plan is read-only. Apply and undo are the only commands that touch files."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import config as cfgmod, llm, mover


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sloth", description="A slow, undoable folder tidier on a local open-weight model.")
    ap.add_argument("cmd", choices=["plan", "apply", "undo", "status", "report", "run"])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--config", type=Path, default=Path("sloth.toml"))
    ap.add_argument("--pace", type=float, default=0.0, help="seconds to rest between files (slow mode)")
    ap.add_argument("--url", default=llm.DEFAULT_URL)
    ap.add_argument("--ignored-for", default=None, metavar="AGE", help="only touch files neither opened nor modified for this long, e.g. 7d, 36h, 0 (default: sloth.toml, else 7d)")
    ap.add_argument("--nice", type=int, default=0, help="lower this process's CPU priority (0-19)")
    a = ap.parse_args(argv)
    root = a.folder.resolve()
    if not root.is_dir():
        print(f"not a folder: {root}", file=sys.stderr); return 2
    if a.nice:
        os.nice(a.nice)
    if a.cmd == "undo":
        r = mover.undo(root); print(r); return 0 if not r["refused"] else 1
    cfg = cfgmod.load(a.config) if a.cmd in ("plan", "apply", "run") else None
    if cfg and a.ignored_for is not None:
        cfg.ignored_for_days = cfgmod.parse_age(a.ignored_for)
    if cfg:
        print(f"rule: only files untouched for {cfg.ignored_for_days:g} days")
    if a.cmd == "plan":
        print(f"model: {llm.model_name(a.url) if llm.available(a.url) else 'NONE (extension rules only)'}")
        p = mover.make_plan(root, cfg, pace=a.pace, url=a.url)
        n = sum(1 for r in p["rows"] if r["folder"] != "leave")
        print(f"{n} of {len(p['rows'])} files would move; {len(p['skipped'])} left alone (touched recently). Nothing was touched. Run `sloth apply`.")
    elif a.cmd == "report":
        from .report import write_report
        print(write_report(root))
    elif a.cmd == "run":  # for the nightly timer: plan slowly, then apply. Every move is in the ledger, so `sloth undo` reverses it.
        mover.make_plan(root, cfg, pace=a.pace, url=a.url); print(mover.apply_plan(root, cfg))
    elif a.cmd == "apply":
        if not (root / mover.PLAN).exists():
            print("no plan: run `sloth plan` first", file=sys.stderr); return 2
        print(mover.apply_plan(root, cfg))
    else:
        print("plan present" if (root / mover.PLAN).exists() else "no plan", "| ledger present" if (root / mover.LEDGER).exists() else "| no ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
