"""Screenshots from saved evidence: the real plan report and the eval tables. Usage: make_shots.py EVIDENCE_DIR REPORT_HTML OUT_DIR"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ev, report, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
L = lambda n: json.load(open(ev / n))
r1, r2 = L("downloads-eval-run1.json"), L("downloads-eval-run2-blindname-prompt.json")
def row(label, s):
    return (f"<tr><td>{label}</td><td>{s['right_moves']}</td><td class='{'bad' if s['wrong_moves'] else 'ok'}'>{s['wrong_moves']}</td>"
            f"<td>{s['left_but_should_move']}</td><td>{s['left_correctly']}</td></tr>")
css = ("body{font:18px/1.5 system-ui,sans-serif;margin:0;padding:32px 40px;color:#1d2330;background:#fff;width:1100px}h2{margin:.2rem 0 .4rem}"
       "table{border-collapse:collapse;width:100%;margin-bottom:1.6rem}th,td{padding:.5rem .8rem;border-bottom:1px solid #d9dde5;text-align:left}"
       "th{background:#f1f3f7}.bad{color:#a02a2a;font-weight:700}.ok{color:#14663a;font-weight:700}small{color:#5d6679}")
hdr = "<tr><th>Method</th><th>Right moves</th><th>Wrong moves</th><th>Left, should have moved</th><th>Left, correctly</th></tr>"
ad = r2["active_files_disturbed"]
html = (f"<style>{css}</style><h2>Fictional Downloads folder: {r2['total_files']} files, {r2['eligible_files']} forgotten for 7+ days</h2>"
        f"<table>{hdr}{row('Extension rules (no model, no age rule)', r2['baseline_on_eligible'])}"
        f"{row('Sloth, first prompt', r1['sloth_on_eligible'])}{row('Sloth, after the blind-name prompt', r2['sloth_on_eligible'])}</table>"
        f"<h2>Files touched in the last 7 days: {ad['of']}</h2><table><tr><th>Method</th><th>Active files moved</th></tr>"
        f"<tr><td>Extension rules</td><td class='bad'>{ad['baseline']} of {ad['of']}</td></tr><tr><td>Sloth (7-day rule)</td><td class='ok'>0 of {ad['of']}</td></tr></table>"
        f"<small>Wrong move = a file put in a folder other than its label (or any move of a file labelled leave). Table scores the {r2['eligible_files']} eligible files only. Source: evidence/r2/*.json</small>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1180, "height": 600}, device_scale_factor=2)
    pg.set_content(html); pg.screenshot(path=str(out / "eval-tables.png"), full_page=True)
    pg2 = b.new_page(viewport={"width": 1100, "height": 800}, device_scale_factor=2)
    pg2.goto(report.resolve().as_uri()); pg2.screenshot(path=str(out / "plan-report.png"), full_page=False)
    b.close()
print("ok")
