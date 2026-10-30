"""Export the carousel: seven PNGs, one seven-page PDF and a contact sheet.

Run from the project folder:
    python export.py                                   (carousel/ -> exports/)
    python export.py carousel-mixed exports/mixed-backgrounds
Needs Google Chrome, Pillow and PyMuPDF (pip install pymupdf).
"""
import pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "carousel")
OUT = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "exports")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
W, H = 1080, 1350
slides = sorted(SRC.glob("slide-0[1-7].html"))
OUT.mkdir(parents=True, exist_ok=True)

def chrome(*args):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--allow-file-access-from-files",
                    "--virtual-time-budget=4000", *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 1. PNGs
pngs = []
for s in slides:
    p = OUT / f"RSTE-editors-{s.stem[-2:]}.png"
    chrome(f"--window-size={W},{H}", f"--screenshot={p}", s.as_uri())
    im = Image.open(p)
    assert im.size == (W, H), (p, im.size)
    pngs.append(p)

# 2. PDF: one page per slide, vector text, built from the same HTML
mains = [re.search(r"<main.*?</main>", s.read_text(encoding="utf-8"), re.S).group(0) for s in slides]
print_html = SRC / "_print.html"
print_html.write_text(
    '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>RSTE editors</title>'
    '<link rel="stylesheet" href="style.css"><style>'
    f"@page {{ size: {W/96}in {H/96}in; margin: 0; }}"
    "html, body { height: auto; background: var(--orange); } .slide { break-after: page;}"
    "* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }"
    "</style></head><body>" + "\n".join(mains) + "</body></html>", encoding="utf-8")
pdf = OUT / "RSTE-editors-carousel.pdf"
chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf}", print_html.as_uri())
print_html.unlink()
# Chrome rounds the page height up to 1013.04 pt, leaving a sub-pixel unpainted strip.
# Clamp every page to exactly 1080 x 1350 px (810 x 1012.5 pt).
import pymupdf
doc = pymupdf.open(pdf)
for page in doc:
    mb = page.mediabox                      # PDF coordinates: origin bottom-left
    box = pymupdf.Rect(0, mb.y1 - H * 0.75, W * 0.75, mb.y1)   # keep the top 1350 px
    page.set_mediabox(box)
doc.save(pdf.with_suffix(".tmp.pdf"), garbage=3, deflate=True)
doc.close()
pdf.with_suffix(".tmp.pdf").replace(pdf)

# 3. Contact sheet
s = 0.3; tw, th = int(W * s), int(H * s); gap = 24; pad = 48
sheet = Image.new("RGB", (pad * 2 + 4 * tw + 3 * gap, pad * 2 + 2 * th + gap + 40), "#ffffff")
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)
for i, p in enumerate(pngs):
    x = pad + (i % 4) * (tw + gap); y = pad + (i // 4) * (th + gap + 40)
    sheet.paste(Image.open(p).resize((tw, th), Image.LANCZOS), (x, y))
    d.text((x, y + th + 8), p.name, fill="#333333", font=font)
sheet.save(OUT / "RSTE-editors-contact-sheet.png")
print("exported", len(pngs), "slides,", pdf.name)
