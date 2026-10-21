"""Build a FICTIONAL "Downloads" folder: invoices, screenshots, installers, manuals and papers, tickets, memes.
Every person, shop, product and number is invented; the images are generated placeholders, the installers are random bytes.
Each file gets an age (mtime) and a few were "opened" recently (atime), so the 7-day rule has something to decide.
Usage: make_downloads_folder.py OUT_DIR   (writes meta.json next to OUT_DIR, not inside it)
Run it last-thing: anything that reads a file afterwards can change its access time."""
import json, os, random, sys, time
from pathlib import Path

R = random.Random(20261020)
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
NOW = time.time(); DAY = 86400
meta, used, pending = {}, set(), []

SHOPS = ["Corner Mart", "Blue Heron Cafe", "Pine Street Hardware", "Lumen Electronics", "Daily Bread Bakery", "Northwind Books", "Kite & Co Opticians"]
CITIES = ["Lisbon", "Kyoto", "Nairobi", "Oslo", "Lima", "Hanoi", "Tallinn"]
APPS = [("code-editor-setup-x64-1.88.1", ".exe"), ("scripting-runtime-3.12.2-amd64", ".exe"), ("js-runtime-v20.11.1-x64", ".msi"), ("container-tool-installer", ".dmg"),
        ("notes-app_1.5.12_amd64", ".deb"), ("media-player-3.0.20-win64", ".exe"), ("archiver-setup-x64", ".exe"), ("image-editor-setup-2.10.36", ".exe"),
        ("web-browser-125.0.tar", ".bz2"), ("video-meeting_amd64", ".deb"), ("usb-writer-4.4", ".exe"), ("disk-flasher-1.18.12", ".AppImage")]
MEME_NAMES = ["when_the_build_passes", "me_on_monday", "social_IMG_1698452", "image(3)", "image(7)", "cat_laptop", "no_one_ever", "received_88231", "IMG-20260811-chat0004",
              "this_is_fine_remix", "two_panel_but_make_it_tea", "monday_mood", "wp_final_form", "unnamed(1)"]
MANUALS = ["Aqua pressure cooker model PC-45", "Halden 20L microwave oven", "Sunra desk fan SF-12", "Kelvin router KR-300", "Orbit vacuum cleaner V2"]
PAPERS = ["sparse attention for long documents", "a survey of quantisation methods", "learning rate warm-up revisited", "federated averaging with stragglers"]
JUNKNAME = ["scan0042", "document", "final", "download", "file(2)", "doc1", "temp", "untitled", "attachment", "x", "output", "Untitled1", "copy of copy", "latest"]


def add(cat, name, age, opened=None, kind="bytes", content=b""):
    """Queue a file. age = days since modified; opened = days since last opened (default: never since modified)."""
    base = name; k = 1
    while name in used:
        stem, dot, ext = base.rpartition("."); name = f"{stem}({k}).{ext}"; k += 1
    used.add(name)
    pending.append((cat, name, age, age if opened is None else opened, kind, content))


def old(): return round(R.uniform(9, 210), 1)
def fresh(): return round(R.uniform(0.1, 5.5), 1)


def invoice_pdf():
    s = R.choice(SHOPS)
    return (f"INVOICE #{R.randint(1000, 9999)}\n{s} (fictional)\nDate: 2026-0{R.randint(1, 9)}-{R.randint(10, 28)}\n"
            f"Items: {R.randint(1, 5)} x item, subtotal {R.randint(200, 9000)}.00\nTax 5%\nTotal due: {R.randint(300, 9500)}.00\nPayment received, thank you.")


def ticket_pdf():
    c = R.choice(CITIES)
    return (f"BOARDING PASS (fictional airline)\nPassenger: A. Example\nFlight XY{R.randint(100, 999)}  Gate {R.choice('ABCD')}{R.randint(1, 30)}\n"
            f"To: {c}\nDeparts 2026-1{R.randint(0, 2)}-{R.randint(10, 28)} {R.randint(5, 22)}:{R.choice(['05', '20', '45'])}\nSeat {R.randint(1, 40)}{R.choice('ABCDEF')}")


def manual_pdf():
    m = R.choice(MANUALS)
    return (f"USER MANUAL - {m} (fictional)\nSafety: read all instructions before first use. Do not immerse the unit in water.\n"
            f"1. Unpacking  2. First use  3. Cleaning and care  4. Troubleshooting\nWarranty: {R.randint(1, 3)} years from purchase with proof of purchase.")


def paper_pdf():
    t = R.choice(PAPERS)
    return (f"{t.capitalize()}\nA. Example, B. Sample (fictional authors)\nAbstract. We study {t} and propose a simple method. "
            f"Experiments on {R.randint(3, 9)} benchmarks show consistent gains.\n1 Introduction\nRelated work is discussed in Section 2.")


# --- invoices-receipts
for _ in range(6): add("invoices-receipts", R.choice(JUNKNAME) + ".pdf", old(), kind="pdf", content=invoice_pdf())
for _ in range(3): add("invoices-receipts", R.choice(JUNKNAME) + ".txt", old(), kind="text",
                      content=f"Receipt\n{R.choice(SHOPS)} (fictional)\nCard ending {R.randint(1000, 9999)}\nAmount paid: {R.randint(100, 5000)}.00\nKeep for warranty and tax filing.")
for _ in range(2): add("invoices-receipts", R.choice(JUNKNAME) + ".eml", old(), kind="text",
                      content=f"Subject: Your payment of {R.randint(100, 5000)}.00 was received\nFrom: billing@{R.choice(SHOPS).split()[0].lower()}.example\n\nThanks for your payment. Your invoice is attached.")
# --- travel-tickets
for _ in range(3): add("travel-tickets", R.choice(JUNKNAME) + ".pdf", old(), kind="pdf", content=ticket_pdf())
for _ in range(2): add("travel-tickets", R.choice(JUNKNAME) + ".txt", old(), kind="text",
                      content=f"Hotel booking confirmation (fictional)\n{R.choice(CITIES)} Riverside Inn\nCheck-in 2026-11-{R.randint(1, 20):02d}\nBooking ref {R.randint(10000, 99999)}\nFree cancellation until 48 hours before arrival.")
# --- manuals-and-papers
for _ in range(4): add("manuals-and-papers", R.choice(JUNKNAME) + ".pdf", old(), kind="pdf", content=manual_pdf())
for _ in range(4): add("manuals-and-papers", R.choice(JUNKNAME) + ".pdf", old(), kind="pdf", content=paper_pdf())
# --- screenshots (png placeholders; named the way phones and desktops name them)
for i in range(9):
    d = R.randint(1, 9)
    nm = R.choice([f"Screenshot 2026-0{d}-{R.randint(10, 28)} at {R.randint(8, 22)}.{R.randint(10, 59)}.{R.randint(10, 59)}.png",
                   f"Screenshot_2026{d:02d}{R.randint(10, 28)}-{R.randint(10, 23)}{R.randint(10, 59)}{R.randint(10, 59)}.png",
                   f"Screen Shot 2026-0{d}-{R.randint(10, 28)}.png"])
    add("screenshots", nm, old(), kind="png", content=nm)
# --- installers (random bytes with a null header so they read as binary)
for nm, ext in APPS[:10]: add("installers", nm + ext, old(), kind="bytes")
# --- memes
for i, nm in enumerate(MEME_NAMES[:12]):
    add("memes", nm + R.choice([".jpg", ".jpg", ".png", ".gif"]), old(), kind="png", content="meme")
# --- genuinely unfilable text (truth: leave)
for t in ["Random thoughts: should I get a plant? maybe a cat. buy batteries?", "Lyrics: la la la, the moon is a lamp on the sea, hold my hand till the morning comes.",
          "Gift ideas for birthdays: socks, a mug, a board game, a kite."]:
    add("leave", R.choice(JUNKNAME) + ".txt", old(), kind="text", content=t)

# --- ACTIVE files: touched in the last days (the 7-day rule must leave these alone). truth = what they would be if tidied.
for _ in range(3): add("invoices-receipts", R.choice(JUNKNAME) + ".pdf", fresh(), kind="pdf", content=invoice_pdf())
add("travel-tickets", "boarding-pass-this-week.pdf", fresh(), kind="pdf", content=ticket_pdf())
for i in range(3):
    nm = f"Screenshot 2026-10-{R.randint(15, 19)} at {R.randint(8, 22)}.{R.randint(10, 59)}.{R.randint(10, 59)}.png"; add("screenshots", nm, fresh(), kind="png", content=nm)
add("installers", "local-llm-runner-linux-amd64.deb", 0.4, kind="bytes")
add("installers", "disk-flasher-1.18.12.AppImage", 2.0, kind="bytes")
add("memes", "monday_mood_NEW.jpg", 0.7, kind="png", content="meme")
add("manuals-and-papers", "paper-to-read-tonight.pdf", 1.2, kind="pdf", content=paper_pdf())
# --- old but OPENED recently: modified long ago, read in the last days (the rule counts opening)
add("manuals-and-papers", "Kelvin router KR-300 manual.pdf", 95, opened=1.5, kind="pdf", content=manual_pdf())
add("invoices-receipts", "tax-statement-draft.pdf", 120, opened=3.0, kind="pdf", content=invoice_pdf())
add("memes", "this_is_fine_remix_2.png", 60, opened=0.5, kind="png", content="meme")

# --- write everything, then set times LAST
from fpdf import FPDF
from PIL import Image, ImageDraw
for cat, name, age, opened, kind, content in pending:
    p = OUT / name
    if kind == "pdf":
        d = FPDF(); d.add_page(); d.set_font("Helvetica", size=11)
        for line in content.splitlines(): d.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        d.output(str(p))
    elif kind == "png":
        im = Image.new("RGB", (320, 200), (R.randint(40, 220), R.randint(40, 220), R.randint(40, 220)))
        ImageDraw.Draw(im).text((12, 90), "fictional placeholder image", fill=(255, 255, 255))
        fmt = {".jpg": "JPEG", ".gif": "GIF"}.get(p.suffix.lower(), "PNG"); im.save(p, fmt)
    elif kind == "text":
        p.write_text(content)
    else:
        p.write_bytes(b"\x00\x01FICTIONAL-INSTALLER\x00" + R.randbytes(2048))
    os.utime(p, (NOW - opened * DAY, NOW - age * DAY))
    meta[name] = {"truth": cat, "modified_days_ago": age, "opened_days_ago": opened}
(OUT.parent / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
fresh_n = sum(1 for m in meta.values() if min(m["modified_days_ago"], m["opened_days_ago"]) < 7)
print(len(meta), "files;", fresh_n, "touched in the last 7 days;", sorted({m["truth"] for m in meta.values()}))
