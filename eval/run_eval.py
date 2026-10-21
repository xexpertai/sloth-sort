"""run_eval.py DIR CONFIG META.json OUT.json: plan on DIR with and without the model, score against the labels.
Two questions: (1) of the files sloth is ALLOWED to touch (forgotten for 7+ days), how many land in the right folder, and
(2) how many files you were still using did each approach disturb. A 'leave' truth moved anywhere counts as a wrong move.
The baseline is a plain extension script with no age rule, i.e. what a normal tidy script does."""
import json, sys, time
from pathlib import Path
from sloth_sort import config as cfgmod, classify as C, llm, mover

d, cfgp, metap, outp = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
cfg = cfgmod.load(cfgp); meta = json.loads(Path(metap).read_text())
assert llm.available(), "model server not running"
take, skipped = mover.candidates(d, cfg)
take_names, skip_names = {p.name for p in take}, {n for n, _ in skipped}
allfiles = sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith("."))
def score(preds, only):
    right = wrong = left_should = left_ok = 0
    for n in only:
        t, f = meta[n]["truth"], preds[n]
        if f == "leave":
            left_ok += (t == "leave"); left_should += (t != "leave")
        elif f == t: right += 1
        else: wrong += 1
    return dict(files=len(only), right_moves=right, wrong_moves=wrong, left_correctly=left_ok, left_but_should_move=left_should,
                accuracy=round((right + left_ok) / max(1, len(only)), 3))
base = {p.name: C.baseline(cfg, p) for p in allfiles}
model, rows, secs, t0 = {}, [], 0.0, time.time()
for i, p in enumerate(sorted(take), 1):
    r = C.classify(cfg, p); model[p.name] = r["folder"]; secs += r["seconds"]
    rows.append(dict(file=p.name, truth=meta[p.name]["truth"], baseline=base[p.name], **r))
    print(i, len(take), p.name, "->", r["folder"], r["confidence"], r["seconds"], flush=True)
wall = round(time.time() - t0, 1)
eligible = sorted(take_names)
active = sorted(skip_names)
res = dict(model=llm.model_name(), ignored_for_days=cfg.ignored_for_days, total_files=len(allfiles), eligible_files=len(eligible), active_files_left_alone=len(active),
           baseline_on_eligible=score(base, eligible), sloth_on_eligible=score(model, eligible),
           active_files_disturbed=dict(baseline=sum(1 for n in active if base[n] != "leave"), sloth=0, of=len(active)),
           total_model_seconds=round(secs, 1), wall_seconds=wall, mean_seconds_per_file=round(secs / max(1, len(eligible)), 1),
           skipped=[dict(file=n, why=w) for n, w in skipped], rows=rows)
Path(outp).write_text(json.dumps(res, indent=1)); print(json.dumps({k: res[k] for k in res if k not in ("rows", "skipped")}, indent=1))
