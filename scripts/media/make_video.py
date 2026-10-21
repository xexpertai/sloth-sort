"""Assemble the 40 s video: title card, replayed REAL CLI session (frames from render_term.py), results card, end card.
Narration: Kokoro af_heart (open-source TTS), disclosed on the end card. Usage (in ~/workspace/.video-venv): make_video.py FRAMES_DIR EVAL_PNG OUT_DIR"""
import subprocess, sys, json
from pathlib import Path
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

frames, evpng, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
W, H, FPS, SR = 1920, 1080, 25, 24000
FB = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
FR = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
BG, FG, AMB = (22, 26, 34), (232, 236, 244), (240, 180, 80)
LINES = {
 "s1": "Your downloads are full of files called final, and final final. I hired a sloth that only touches what you forgot for a week.",
 "s2": "Sloth sort only touches files you have forgotten: nothing opened or changed for seven days. The three recent files are left alone straight away. A small open model reads each of the rest, picks a folder, and moves it. This is a real run on fictional files, an excerpt of fourteen, sped up eight times. Then undo puts every file back.",
 "s3": "Fictional folder, seventy two files: all fourteen active files left alone, forty two of fifty eight filed right, none wrong, thirteen left alone.",
 "s3b": "My real Downloads, seven files: two recent left alone, four filed, undo exact. Not scored.",
 "s4": "Sloth sort, by Harsha Shinday. AI assisted, AI voice.",
}
from kokoro import KPipeline
pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
aud = {}
for k, t in LINES.items():
    a = np.concatenate([x[2].numpy() if hasattr(x[2], "numpy") else x[2] for x in pipe(t, voice="af_heart", speed=1.0)])
    aud[k] = a; print(k, round(len(a) / SR, 1), "s")
def fit(d, text, mk, size, maxw=W - 160, bold=False):
    while d.textlength(text, font=mk(size)) > maxw: size -= 2
    return mk(size)
def card(path, title, sub, small=None, color=FG):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((W // 2, 430), title, font=fit(d, title, FB, 84), fill=color, anchor="mm")
    d.text((W // 2, 560), sub, font=fit(d, sub, FR, 44), fill=AMB, anchor="mm")
    if small:
        for i, s in enumerate(small): d.text((W // 2, 760 + i * 56), s, font=fit(d, s, FR, 38), fill=(180, 188, 204), anchor="mm")
    im.save(path)
card(out / "title.png", "I hired a sloth to tidy a Downloads folder", "it only touches files forgotten for 7 days", ["Replay: a FICTIONAL 72-file folder (excerpt: 14 files)", "Gemma 4 E2B on a laptop CPU"])
card(out / "real.png", "Real run: my own Downloads (a copy)", "7 files: 2 used lately left alone, 4 old ones filed, 1 system file skipped", [".exe -> installers   |   .jpg, .png, .png -> screenshots", "undo: all 7 files byte-identical (SHA-256)", "file names hidden  |  the 4 moves are not scored", "plan 50.7 s, apply 0.12 s"])
card(out / "end.png", "sloth-sort", "by Harsha Shinde", ["Built with Claude Code (AI-assisted); I reviewed, ran and scored it.", "Narration: AI voice (Kokoro, open source).", "Replay and big results: fictional demo files. The 7-file run: my real Downloads, names hidden."])
res = Image.open(evpng).convert("RGB"); sc = min((W - 160) / res.width, (H - 120) / res.height)
res = res.resize((int(res.width * sc), int(res.height * sc)), Image.LANCZOS)
im = Image.new("RGB", (W, H), (255, 255, 255)); im.paste(res, ((W - res.width) // 2, 30)); d = ImageDraw.Draw(im)
d.rectangle([0, H - 84, W, H], fill=BG)
BAN = "fictional 72 files  |  active files moved: 0 of 14 (extension script: 14 of 14)  |  58 old files: 42 right, 0 wrong, 13 left"
d.text((W // 2, H - 42), "fictional 72 files  |  active files moved: 0 of 14 (extension script: 14 of 14)  |  58 old files: 42 right, 0 wrong, 13 left", font=fit(d, BAN, FB, 30, W - 80), fill=AMB, anchor="mm")
im.save(out / "results.png")
dur = {k: len(a) / SR for k, a in aud.items()}
seg = {"s1": max(3.6, dur["s1"] + 0.8), "s2": max(24.3, dur["s2"] + 1.0), "s3": dur["s3"] + 0.7, "s3b": dur["s3b"] + 0.8, "s4": max(4.8, dur["s4"] + 0.8)}
# audio timeline
total = sum(seg.values()); mix = np.zeros(int(total * SR) + SR)
t0 = 0.0
for k in ["s1", "s2", "s3", "s3b", "s4"]:
    off = int((t0 + (0.4 if k != "s2" else 0.9)) * SR); mix[off: off + len(aud[k])] += aud[k]; t0 += seg[k]
# generated background music (no samples): slow A-minor pad with a soft arpeggio, under the voice
tt = np.arange(len(mix)) / SR; pad = np.zeros(len(mix))
for f, g in [(110.0, 1.0), (164.81, 0.7), (220.0, 0.6), (261.63, 0.5), (329.63, 0.35)]:
    pad += g * np.sin(2 * np.pi * f * tt + 0.3 * np.sin(2 * np.pi * 0.11 * tt))
pad *= 0.7 + 0.3 * np.sin(2 * np.pi * tt / 8.0)
arp = np.zeros(len(mix)); notes = [220.0, 261.63, 329.63, 392.0, 329.63, 261.63]
for i in range(int(tt[-1] / 0.75)):
    s = int(i * 0.75 * SR); n = int(0.7 * SR); e = np.exp(-np.arange(n) / (0.18 * SR)); f = notes[i % 6]
    seg_ = 0.5 * np.sin(2 * np.pi * f * np.arange(n) / SR) * e; arp[s:s + n] += seg_[: max(0, min(n, len(arp) - s))]
bed = (pad / np.abs(pad).max() * 0.05 + arp * 0.03)
fade = np.minimum(1.0, np.minimum(tt / 1.5, (tt[-1] - tt) / 2.0)); bed *= fade
mix = np.clip(mix + bed, -1, 1)
sf.write(out / "vo_raw.wav", mix, SR, subtype="PCM_16")
j = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out / "vo_raw.wav"), "-af", "acompressor=threshold=0.05:ratio=4:attack=5:release=120:makeup=2,loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(j[j.rfind("{"): j.rfind("}") + 1])
af0 = "acompressor=threshold=0.05:ratio=4:attack=5:release=120:makeup=2,loudnorm=I=-14:TP=-1.6:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true" % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"])
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "vo_raw.wav"), "-af", af0, "-ar", "48000", "-ac", "2", str(out / "vo0.wav")], check=True)
def lufs(f):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-af", "loudnorm=I=-14:TP=-1:print_format=json", "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    d = json.loads(m[m.rfind("{"): m.rfind("}") + 1]); return float(d["input_i"]), float(d["input_tp"])
i0, tp0 = lufs(out / "vo0.wav"); gain = -14.0 - i0; print("vo LUFS", i0, "tp", tp0, "gain", round(gain, 2))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "vo0.wav"), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=disabled", str(out / "vo.wav")], check=True)
print("final vo", lufs(out / "vo.wav"))
def still(png, secs, name):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(png), "-t", f"{secs:.2f}", "-vf", f"format=yuv420p,fade=t=in:d=0.3,fade=t=out:st={max(0,secs-0.3):.2f}:d=0.3", "-c:v", "libx264", "-crf", "18", str(out / name)], check=True)
still(out / "title.png", seg["s1"], "v1.mp4"); still(out / "results.png", seg["s3"], "v3.mp4"); still(out / "end.png", seg["s4"], "v4.mp4"); still(out / "real.png", seg["s3b"], "v3b.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.png"), "-vf", f"tpad=stop_mode=clone:stop_duration={seg['s2']:.2f},format=yuv420p,fade=t=in:d=0.3,fade=t=out:st={seg['s2']-0.3:.2f}:d=0.3", "-t", f"{seg['s2']:.2f}", "-c:v", "libx264", "-crf", "18", str(out / "v2.mp4")], check=True)
(out / "list.txt").write_text("".join(f"file '{n}'\n" for n in ["v1.mp4", "v2.mp4", "v3.mp4", "v3b.mp4", "v4.mp4"]))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(out / "list.txt"), "-i", str(out / "vo.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / "sloth-sort-demo.mp4")], check=True)
print("total", round(total, 1), "s ->", out / "sloth-sort-demo.mp4")
