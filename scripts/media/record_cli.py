"""Run REAL sloth commands on a 14-file subset of the fictional Downloads folder and log (seconds, text) for each output line.
Usage: record_cli.py DOWNLOADS_DIR META_JSON OUT_JSON   (the GIF/video renderer replays this log, sped up and labelled as such)
The subset: 11 forgotten files across all folders, plus 3 you touched lately (2 modified, 1 only opened) that must stay put."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

src, meta, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), Path(sys.argv[3])
work = Path("/tmp/claude-1000/gifwork"); shutil.rmtree(work, ignore_errors=True); (work / "Downloads").mkdir(parents=True)
def active(m): return min(m["modified_days_ago"], m["opened_days_ago"]) < 7
want = {"invoices-receipts": 2, "travel-tickets": 1, "manuals-and-papers": 2, "screenshots": 2, "installers": 2, "memes": 1, "leave": 1}
chosen = []
for n, m in sorted(meta.items()):
    if not active(m) and want.get(m["truth"], 0) > 0 and (src / n).suffix.lower() != ".bz2":
        chosen.append(n); want[m["truth"]] -= 1
chosen += ["paper-to-read-tonight.pdf", "monday_mood_NEW.jpg", "Kelvin router KR-300 manual.pdf"]
for n in chosen:
    st = os.stat(src / n)  # copy without opening: shutil.copy2 would read the file and stamp today's date as its access time
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from sloth_sort.reader import open_untouched
    with open_untouched(src / n) as fi, open(work / "Downloads" / n, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    os.utime(work / "Downloads" / n, (st.st_atime, st.st_mtime))
env = dict(os.environ, PYTHONUNBUFFERED="1")
log = []; T0 = time.time()
def run(cmd):
    log.append((round(time.time() - T0, 2), "cmd", cmd))
    pr = subprocess.Popen(cmd, shell=True, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    for line in pr.stdout:
        log.append((round(time.time() - T0, 2), "out", line.rstrip("\n")))
    pr.wait()
S = "/home/harsha/workspace/dev-hacktoberfest/week3/sloth-sort/.venv/bin/sloth"
C = "/home/harsha/workspace/dev-hacktoberfest/week3/sloth-sort/eval/downloads.toml"
run("ls -l --time-style=+%F Downloads | sed 's/^[^ ]* *[^ ]* *[^ ]* *[^ ]* *//'")
run(f"{S} plan Downloads --config demo.toml --nice 19".replace("demo.toml", C))
run(f"{S} apply Downloads --config demo.toml".replace("demo.toml", C))
run("ls Downloads")
run(f"{S} undo Downloads")
out.write_text(json.dumps(log, indent=1)); print(len(log), "lines,", round(time.time() - T0, 1), "s real time")
