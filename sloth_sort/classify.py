"""Pick a folder for one file. The model proposes; code decides what is allowed."""
from __future__ import annotations

from pathlib import Path

from . import llm
from .config import LEAVE, Config
from .reader import snippet

SYSTEM = ("You tidy a messy folder. You are given one file (name, size, and the start of its text) and a list of "
          "target folders with one-line descriptions. Choose the single best folder by what the file CONTAINS, not "
          "by its name. If no folder clearly fits, choose 'leave'. Answer in JSON.")


def schema(cfg: Config) -> dict:
    return {"type": "object", "additionalProperties": False,
            "properties": {"folder": {"type": "string", "enum": cfg.names + [LEAVE]},
                           "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                           "reason": {"type": "string", "maxLength": 140}},
            "required": ["folder", "confidence", "reason"]}


def baseline(cfg: Config, path: Path) -> str:
    """No model: extension match only. This is what a normal tidy script does."""
    for f in cfg.folders:
        if path.suffix.lower() in f.ext:
            return f.name
    return LEAVE


def build_messages(cfg: Config, path: Path) -> list[dict]:
    kind, text = snippet(path, cfg.snippet_chars)
    menu = "\n".join(f"- {f.name}: {f.desc}" for f in cfg.folders) + f"\n- {LEAVE}: none of the above clearly fits"
    body = f"File name: {path.name}\nSize: {path.stat().st_size} bytes\n"
    body += f"Start of contents:\n{text}" if text else (
        "Contents: you cannot see inside this file (an image, installer or other binary). Go by the file name only. "
        "Choose a folder only if the NAME itself clearly says where it belongs (for example 'Screenshot 2026-03-18 at 10.32.11.png' "
        "or 'scripting-runtime-3.12-setup.exe'). A vague name such as 'IMG_123.jpg' or 'image(3).png' tells you nothing: answer 'leave'.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Folders:\n{menu}\n\n{body}"}]


def classify(cfg: Config, path: Path, *, url: str = llm.DEFAULT_URL) -> dict:
    """Return {'folder','confidence','reason','source','seconds'}. Guards live here, not in the model."""
    kind, _ = snippet(path, 50)
    for f in cfg.folders:                  # guard 0: a strict folder's extension is a rule the model never gets to argue with
        if f.strict and path.suffix.lower() in f.ext:
            return {"folder": f.name, "confidence": "high", "reason": f"rule: {path.suffix} always goes to {f.name}",
                    "source": "rule", "seconds": 0.0}
    try:
        out, secs = llm.chat(build_messages(cfg, path), schema(cfg), url=url)
    except llm.LLMUnavailable:
        return {"folder": baseline(cfg, path), "confidence": "low", "reason": "no model running: extension rule",
                "source": "baseline", "seconds": 0.0}
    folder, conf = out.get("folder", LEAVE), out.get("confidence", "low")
    if folder not in cfg.names:            # guard 1: unknown folder -> leave
        folder = LEAVE
    strict = {f.name for f in cfg.folders if f.strict}
    if folder in strict:                   # guard 0b: nothing else may enter a strict folder
        out["reason"] = f"{folder} only takes its own extensions, left alone: " + out.get("reason", "")
        folder = LEAVE
    if conf == "low" and folder != LEAVE:  # guard 2: unsure -> leave it where it is
        out["reason"] = "low confidence, left alone: " + out.get("reason", "")
        folder = LEAVE
    if kind == "binary" and conf != "high":  # guard 3: nothing to read -> the model must be sure
        folder = LEAVE
    return {"folder": folder, "confidence": conf, "reason": out.get("reason", ""), "source": "model", "seconds": secs}
