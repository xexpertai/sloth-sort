"""Config: the user names their folders and says in one line what belongs in each."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

LEAVE = "leave"  # the model's (and the code's) way of saying "I don't know, don't touch it"


@dataclass
class Folder:
    name: str
    desc: str
    ext: list[str] = field(default_factory=list)  # the no-model baseline; also the hard rule when strict
    strict: bool = False  # strict: these extensions always go here, nothing else may go here (the user's rule beats the model)


@dataclass
class Config:
    folders: list[Folder]
    snippet_chars: int = 1200
    ignored_for_days: float = 7.0  # the core rule: only files neither opened nor modified for this long are touched; 0 = no rule

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.folders]


def parse_age(v) -> float:
    """'7d', '36h', '90m' or a bare number of days -> days (float). The rule is 'how long have I ignored this file?'."""
    if isinstance(v, (int, float)):
        return float(v)
    v = str(v).strip().lower()
    mult = {"d": 1.0, "h": 1 / 24, "m": 1 / 1440}
    if v and v[-1] in mult:
        return float(v[:-1]) * mult[v[-1]]
    return float(v)


def load(path: str | Path) -> Config:
    raw = tomllib.loads(Path(path).read_text())
    folders = []
    for name, v in raw.get("folders", {}).items():
        if name == LEAVE or "/" in name or name.startswith("."):
            raise ValueError(f"bad folder name {name!r}")
        if isinstance(v, str):
            v = {"desc": v}
        folders.append(Folder(name, v["desc"], [e.lower() for e in v.get("ext", [])], bool(v.get("strict", False))))
    if len(folders) < 2:
        raise ValueError("need at least two folders")
    s = raw.get("settings", {})
    return Config(folders, int(s.get("snippet_chars", 1200)), parse_age(s.get("ignored_for", "7d")))
