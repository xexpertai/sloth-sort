"""Replay a recorded REAL CLI session (cli-capture.json) as terminal frames. Time is compressed by SPEED and the badge says so.
Only cosmetic edits: the long venv path in commands is shown as `sloth`, and the typing of commands is animated.
Usage: render_term.py capture.json OUT_DIR [SPEED] [FPS]"""
import json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

cap = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 8; FPS = int(sys.argv[4]) if len(sys.argv) > 4 else 12
import os
K = float(os.environ.get("SCALE", "1")); W, H = int(1280 * K), int(720 * K); PADX, PADY, FS, LH = int(36 * K), int(96 * K), int(22 * K), int(29 * K)
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", FS)
FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", int(20 * K))
ROWS = (H - PADY - int(30 * K)) // LH
BG, FG, GREEN, DIM, AMBER = (22, 26, 34), (226, 230, 238), (110, 216, 150), (130, 140, 158), (240, 180, 80)
MAXC = int((W - 2 * PADX) // (13.2 * K))  # DejaVu Mono 22px is ~13.2 px per char

def short(cmd):
    cmd = re.sub(r"/\S*/\.venv/bin/sloth", "sloth", cmd)
    return re.sub(r"--config \S+", "--config downloads.toml", cmd)

def clip(s):
    return s if len(s) <= MAXC else s[: MAXC - 1] + "…"

# build event list: (time_s_compressed, kind, text)
ev, t_prev_real, tc = [], 0.0, 0.0
for t, kind, text in cap:
    if kind == "cmd":
        tc += 0.5; ev.append(("type", tc, short(text))); tc += len(short(text)) * 0.012 + 0.35
        t_prev_real = t
    else:
        tc += min((t - t_prev_real) / SPEED, 2.0) if t - t_prev_real > 0.2 else 0.02
        t_prev_real = t; ev.append(("line", tc, text))
total = tc + 2.5
def frame(now):
    lines = []  # (text, color)
    for kind, t, text in ev:
        if t > now and kind == "line": break
        if kind == "type":
            n = int(max(0, min(len(text), (now - (t - len(text) * 0.012 - 0.35)) / 0.012))) if now < t else len(text)
            if now < t - len(text) * 0.012 - 0.35: break
            lines.append(("$ " + text[:n], GREEN))
            if now < t: break
        else:
            col = DIM if text.startswith("[") and "->" in text and "(low" in text else FG
            if "leave" in text and text.startswith("["): col = AMBER
            if text.startswith("{") or text.startswith("moved") or text.startswith("restored"): col = (150, 190, 255)
            lines.append((text, col))
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, int(64 * K)], fill=(34, 40, 52))
    d.text((PADX, int(18 * K)), "sloth-sort | real run, fictional files | excerpt: 14 of 72", font=FB, fill=FG)
    badge = f"sped up {SPEED:g}x | Gemma 4 E2B, CPU"
    d.text((W - PADX - FB.getlength(badge), int(18 * K)), badge, font=FB, fill=AMBER)
    y = PADY
    for text, col in lines[-ROWS:]:
        d.text((PADX, y), clip(text), font=F, fill=col); y += LH
    return im
n = int(total * FPS)
for i in range(n):
    frame(i / FPS).save(out / f"f{i:04d}.png")
print(n, "frames,", round(total, 1), "s")
