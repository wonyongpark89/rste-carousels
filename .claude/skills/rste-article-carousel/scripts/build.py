"""Render one RSTE article carousel from verified metadata and written content.

    python build.py <article_dir>

Every file in <article_dir> starts with the first author's family name, e.g. "mesci-".
<article_dir> holds:
  <name>-metadata.json  verified source facts (fetch_metadata.py, then confirmed by hand)
  <name>-content.json   the written text for pages 2-3 and the LinkedIn caption
and receives:
  <name>-slide-1.png <name>-slide-2.png <name>-slide-3.png <name>-carousel.pdf <name>-caption.txt html/

The design lives only in ../template; article facts live only in <article_dir>.
Needs Google Chrome, Pillow and PyMuPDF (pip install pymupdf).
"""
import html, json, os, pathlib, re, shutil, subprocess, sys, unicodedata

SKILL = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "template"
ASSETS = SKILL / "assets"
W, H = 1080, 1350
CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/opt/pw-browsers/chromium",
]
CHROME = next((c for c in CHROME_CANDIDATES if c and pathlib.Path(c).exists()), None)

# LinkedIn has no formatting, so emphasis uses Unicode mathematical letters.
def _styled(s, upper, lower, digit):
    out = []
    for ch in s:
        if "A" <= ch <= "Z": out.append(chr(upper + ord(ch) - 65))
        elif "a" <= ch <= "z": out.append(chr(lower + ord(ch) - 97))
        elif "0" <= ch <= "9": out.append(chr(digit + ord(ch) - 48))
        else: out.append(ch)
    return "".join(out)


def bold_serif(s):
    return _styled(s, 0x1D400, 0x1D41A, 0x1D7CE)


def bold_sans(s):
    return _styled(s, 0x1D5D4, 0x1D5EE, 0x1D7EC)


def caption_text(cap, doi_url):
    """One paragraph: emoji, bold-serif question, intro (with **phrase** in bold sans), DOI link.
    Then a blank line and the hashtags."""
    sans = lambda t: re.sub(r"\*\*(.+?)\*\*", lambda m: bold_sans(m.group(1)), t)
    para = f"{cap.get('emoji', '🔍')} {bold_serif(cap['question'])} {sans(cap['intro'])} {doi_url}"
    return para + "\n\n" + " ".join("#" + h.lstrip("#") for h in cap["hashtags"])


def file_prefix(meta):
    """First author's family name in plain lowercase ASCII, e.g. 'Günkut Mesci' -> 'mesci'."""
    a = meta["authors"][0]
    name = a.get("family") or a["name"].split()[-1]
    name = re.sub("[\u2010-\u2015\u2212]", "-", name)   # typographic hyphens and dashes count as hyphens
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "article"


def find_one(d, suffix):
    """The article's <prefix>-metadata.json / -content.json (or the old unprefixed name)."""
    hits = sorted(d.glob(f"*-{suffix}")) or sorted(d.glob(suffix))
    if len(hits) != 1:
        fail(f"expected one *{suffix} in {d}, found {len(hits)}")
    return hits[0]


MIN_WORDS, MAX_WORDS = 40, 52   # per page, all bullets together

# Each series shares the layout; it sets the page 1 tag, the two question pages and the colour theme
# (style.css: .series-<name>). content.json picks one with "series"; the default is "new".
SERIES = {
    "new": {
        "tag": "New article",
        "pages": (("investigate", "What did the<br>researchers<br>investigate?"),
                  ("find", "What did<br>they find?")),
    },
    "archive": {
        "tag": "From the archive",           # followed by the year of the issue
        "pages": (("contribution", "What did<br>this paper<br>contribute?"),
                  ("today", "What has<br>changed, and<br>why it matters")),
    },
}


def series_of(meta, content):
    s = content.get("series") or meta.get("series") or "new"
    if s not in SERIES:
        fail(f"unknown series {s!r}; use one of {', '.join(SERIES)}")
    return s


def issue_year(meta):
    """Year of the issue the article appeared in (print date first: back issues were put online years later)."""
    return (meta.get("published_print") or meta.get("published_online") or "")[:4]


def fail(msg):
    sys.exit("BUILD STOPPED: " + msg)


WJ = "⁠"  # word joiner: no line break after a hyphen, invisible, needs no glyph


def plain(text):
    """Bullet text as a reader sees it: highlight markers removed."""
    return text.replace("==", "")


def glue_hyphens(escaped):
    """Keep hyphenated compounds such as 'open-ended' on one line."""
    return re.sub(r"(\w)-(\w)", lambda m: m.group(1) + "-" + WJ + m.group(2), escaped)


def bullet_html(text):
    """Escape, keep hyphenated compounds whole, and turn ==phrase== into a highlight."""
    out = glue_hyphens(html.escape(text))
    if out.count("==") % 2:
        fail(f"unbalanced == highlight markers in: {text}")
    return re.sub(r"==(.+?)==", lambda m: f'<mark class="hl">{m.group(1)}</mark>', out)


def bullets(content, key):
    items = content["pages"][key]
    if isinstance(items, str):
        fail(f"pages.{key} must be a list of bullet strings")
    return items


def words(text):
    if isinstance(text, list):
        text = " ".join(text)
    return len(re.findall(r"\S+", plain(text)))


# ---------------------------------------------------------------- checks
def check(meta, content):
    if meta.get("missing"):
        fail("metadata.json still lists missing information; confirm it and clear 'missing':\n  - "
             + "\n  - ".join(meta["missing"]))
    for k in ("doi", "title", "journal", "authors", "abstract"):
        if not meta.get(k):
            fail(f"metadata.json has no {k}")
    provisional = bool(meta.get("provisional"))   # set only by fetch_metadata.py --provisional; the Editor is warned
    if not meta["abstract"].get("text") or ("unverified" in (meta["abstract"].get("source") or "") and not provisional):
        fail("the abstract is not confirmed against the published source")
    for a in meta["authors"]:
        if not a.get("affiliation_first"):
            fail(f"no confirmed first affiliation for {a['name']}")
        check_house_style(a)
    if content.get("doi") != meta["doi"]:
        fail("content.json DOI does not match metadata.json")
    series = series_of(meta, content)
    for (key, _), label in zip(SERIES[series]["pages"], ("page 2", "page 3")):
        if key not in content.get("pages", {}):
            fail(f"{label}: the {series!r} series needs pages.{key}")
        items = bullets(content, key)
        if not 2 <= len(items) <= 4:
            fail(f"{label} has {len(items)} bullets; use 2-4")
        n = words(items)
        if not MIN_WORDS <= n <= MAX_WORDS:
            fail(f"{label} text is {n} words; it must be {MIN_WORDS}-{MAX_WORDS}")
        marks = sum(b.count("==") // 2 for b in items)
        if not 1 <= marks <= len(items):
            fail(f"{label} has {marks} highlights; use one per bullet at most, and at least one")
    cap = content["caption"]
    if "text" in cap:
        # a caption written in full by the Editor is used verbatim; only check it links the article
        if meta["doi_url"] not in cap["text"] and meta["doi"] not in cap["text"]:
            fail("caption.text must include the article's DOI link")
        return words(cap["text"].split("\n#")[0])
    body = " ".join([cap["question"], cap["intro"]])
    n = words(body.replace("**", ""))
    if not 30 <= n <= 55:
        fail(f"caption question and intro are {n} words; aim for 30-55")
    if not 8 <= len(cap["hashtags"]) <= 12:
        fail(f"{len(cap['hashtags'])} hashtags; use 8-12")
    bolds = cap["intro"].count("**") // 2
    if bolds > 2 or "**" in cap["question"]:
        fail("caption: at most two **bold** phrases, in the intro only (the question is set in bold serif)")
    if len(cap.get("emoji", "🔍")) > 2:
        fail("caption: 'emoji' must be a single emoji (the caption uses two in total, with 📄)")
    return n


def display_title(meta):
    """RSTE house style: titles on slides in sentence case (title_display), the published form kept in title.
    The two may differ only in capitalisation, so no word can change."""
    shown = meta.get("title_display") or meta["title"]
    if shown.casefold() != meta["title"].casefold():
        fail(f"title_display differs from the published title by more than capitalisation:\n"
             f"  published: {meta['title']}\n  display:   {shown}")
    return shown


def check_house_style(a):
    """RSTE house style for slides: '[Organisation], [Country]'.
    No department or subunit, no city. Both parts must come from the published first affiliation."""
    disp = a.get("affiliation_display")
    if not disp:
        fail(f"no house-style affiliation_display for {a['name']} "
             f"(published: {a['affiliation_first']!r}); write it as 'Organisation, Country'")
    org, _, country = disp.rpartition(", ")
    published = a["affiliation_first"]
    if not org or not country:
        fail(f"{a['name']}: affiliation_display {disp!r} is not 'Organisation, Country'")
    if not published.rstrip(". ").endswith(country):
        fail(f"{a['name']}: country {country!r} is not the country in the published affiliation {published!r}")
    if org not in published:
        fail(f"{a['name']}: organisation {org!r} does not appear in the published affiliation {published!r}")


# ---------------------------------------------------------------- page 1 data
def affiliation_letters(authors):
    """Group identical (house-style) affiliations; letters follow first appearance in author order."""
    letters, order = {}, []
    for a in authors:
        aff = a["affiliation_display"]
        if aff not in letters:
            letters[aff] = "abcdefghijklmnopqrstuvwxyz"[len(letters)]
            order.append(aff)
    return letters, order


def author_line(authors, letters, show_letters):
    parts = []
    for a in authors:
        name = html.escape(a["name"]).replace(" ", "&nbsp;")
        sup = f"<sup>{letters[a['affiliation_display']]}</sup>" if show_letters else ""
        parts.append(f'<span class="au">{name}{sup}</span>')
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def short_cite(meta):
    fam = [a["family"] or a["name"] for a in meta["authors"]]
    year = issue_year(meta)
    who = fam[0] if len(fam) == 1 else f"{fam[0]} and {fam[1]}" if len(fam) == 2 else f"{fam[0]} et al."
    return f"{who} ({year})" if year else who


# ---------------------------------------------------------------- html
def page(n, body_cls, inner):
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>RSTE article — {n}/3</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main class="slide {body_cls}">
{inner}
</main>
<script src="fit.js"></script>
</body>
</html>
"""


def build_pages(meta, content):
    e = html.escape
    letters, order = affiliation_letters(meta["authors"])
    show = len(order) > 1
    affils = "".join(
        f"<li>{'<sup>' + letters[a] + '</sup>' if show else ''}{e(a)}</li>" for a in order)
    doi = meta["doi"]
    series = series_of(meta, content)
    tag = SERIES[series]["tag"] + (f" · {issue_year(meta)}" if series == "archive" and issue_year(meta) else "")
    p1 = page(1, f"article series-{series}", f"""  <p class="journal">{e(meta['journal']).replace(' &amp; ', '<br>&amp; ')}</p>
  <div class="folio">01/03</div>
  <div class="title-box" data-fit=".title" data-min="44"><p class="tag">{e(tag)}</p><h1 class="title">{glue_hyphens(e(display_title(meta)))}</h1></div>
  <div class="byline-box" data-fit=".authors" data-min="26" data-scale=".affils">
    <p class="authors">{author_line(meta['authors'], letters, show)}</p>
    <ul class="affils">{affils}</ul>
  </div>
  <p class="doi"><span>DOI</span> doi.org/{e(doi)}</p>
  <div class="foot"><img class="publisher" src="taylor-francis-navy.svg" alt="Taylor &amp; Francis Group"></div>""")
    cite = f"<b>{e(short_cite(meta))}</b> · {e(meta['journal'])} · doi.org/{e(doi)}"
    out = [p1]
    for n, (key, heading) in zip((2, 3), SERIES[series]["pages"]):
        out.append(page(n, f"section series-{series}", f"""  <h1 class="heading shout">{heading}</h1>
  <div class="folio">0{n}/03</div>
  <div class="body-box" data-fit=".body" data-min="38"><ul class="body points">{''.join(f'<li>{bullet_html(b)}</li>' for b in bullets(content, key))}</ul></div>
  <p class="cite">{cite}</p>"""))
    return out


# ---------------------------------------------------------------- render
def chrome(*args, capture=False):
    if not CHROME:
        fail("Chrome or Edge not found; set the CHROME environment variable")
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--allow-file-access-from-files",
                        "--virtual-time-budget=5000", *(["--no-sandbox"] if hasattr(os, "geteuid") and os.geteuid() == 0 else []), *args],
                       check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def main(article_dir):
    d = pathlib.Path(article_dir).resolve()
    meta_path, content_path = find_one(d, "metadata.json"), find_one(d, "content.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    content = json.loads(content_path.read_text(encoding="utf-8"))
    cap_words = check(meta, content)

    # every file in the folder starts with the first author's family name
    pre = file_prefix(meta)
    for path, suffix in ((meta_path, "metadata.json"), (content_path, "content.json")):
        if path.name != f"{pre}-{suffix}":
            path.rename(d / f"{pre}-{suffix}")
    for pattern in ("*slide-[123].png", "*carousel.pdf", "*caption.txt"):
        for stale in d.glob(pattern):        # outputs under an earlier naming rule
            if not stale.name.startswith(pre + "-"):
                stale.unlink()

    hd = d / "html"
    hd.mkdir(exist_ok=True)
    for f in TEMPLATE.iterdir():          # style.css, fit.js, hand-drawn marks
        if f.is_file():
            shutil.copy(f, hd / f.name)
    (hd / "fonts").mkdir(exist_ok=True)
    for f in (ASSETS / "fonts").iterdir():
        shutil.copy(f, hd / "fonts" / f.name)
    shutil.copy(ASSETS / "logos" / "taylor-francis-navy.svg", hd / "taylor-francis-navy.svg")

    pages = build_pages(meta, content)
    for i, p in enumerate(pages, 1):
        (hd / f"slide-{i}.html").write_text(p, encoding="utf-8")

    def fitted(i):
        dom = chrome("--dump-dom", (hd / f"slide-{i}.html").as_uri())
        if 'data-fitted="1"' not in dom:
            fail(f"slide {i}: the auto-fit script did not finish (fonts not loaded?)")
        if 'data-overflow="1"' in dom:
            fail(f"slide {i}: text does not fit even at the minimum size; shorten it")
        return [int(x) for x in re.findall(r'data-fitted-size="(\d+)"', dom)]

    # pages 2 and 3 are a pair: if either had to shrink, set both at the smaller size
    sizes = {i: fitted(i) for i in (1, 2, 3)}
    body = min(sizes[2][0], sizes[3][0])
    if sizes[2][0] != sizes[3][0]:
        for i in (2, 3):
            pages[i - 1] = pages[i - 1].replace('<ul class="body points">',
                                                f'<ul class="body points" style="font-size: {body}px">')
            (hd / f"slide-{i}.html").write_text(pages[i - 1], encoding="utf-8")
            fitted(i)

    from PIL import Image
    for i in range(1, 4):
        src = (hd / f"slide-{i}.html").as_uri()
        png = d / f"{pre}-slide-{i}.png"
        chrome(f"--window-size={W},{H}", f"--screenshot={png}", src)
        if Image.open(png).size != (W, H):
            fail(f"{png.name} is not {W}x{H}")

    # PDF from the same pages: vector text, one page each
    mains = [re.search(r"<main.*?</main>", p, re.S).group(0) for p in pages]
    pr = hd / "_print.html"
    pr.write_text('<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>RSTE article carousel</title>'
                  '<link rel="stylesheet" href="style.css"><style>'
                  f"@page {{ size: {W/96}in {H/96}in; margin: 0; }} html, body {{ height: auto; }}"
                  ".slide { break-after: page; } * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }"
                  '</style></head><body>' + "\n".join(mains) + '<script src="fit.js"></script></body></html>',
                  encoding="utf-8")
    pdf = d / f"{pre}-carousel.pdf"
    chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf}", pr.as_uri())
    pr.unlink()
    import pymupdf  # clamp Chrome's rounded page height back to exactly 1080 x 1350 px
    doc = pymupdf.open(pdf)
    for pg in doc:
        mb = pg.mediabox
        pg.set_mediabox(pymupdf.Rect(0, mb.y1 - H * 0.75, W * 0.75, mb.y1))
    if doc.page_count != 3:
        fail(f"PDF has {doc.page_count} pages")
    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf)

    # read the finished PDF back: every source fact and sentence must appear exactly
    norm = lambda t: re.sub(r"\s+", " ", t.replace(WJ, "")).strip()
    doc = pymupdf.open(pdf)
    text = [norm(pg.get_text()) for pg in doc]
    doc.close()
    expected = [(0, display_title(meta), "title"), (0, meta["doi"], "DOI")]
    expected += [(0, a["name"], "author " + a["name"]) for a in meta["authors"]]
    expected += [(0, a["affiliation_display"], "affiliation of " + a["name"]) for a in meta["authors"]]
    keys = [k for k, _ in SERIES[series_of(meta, content)]["pages"]]
    for i, key in zip((1, 2), keys):
        expected += [(i, plain(b), f"page {i + 1} bullet {j}") for j, b in enumerate(bullets(content, key), 1)]
    for i, want, label in expected:
        if norm(want) not in text[i]:
            fail(f"{label} is not reproduced exactly on page {i + 1} of the PDF")

    cap = content["caption"]
    caption = cap["text"].strip() if "text" in cap else caption_text(cap, meta["doi_url"])
    (d / f"{pre}-caption.txt").write_text(caption + "\n", encoding="utf-8")
    print(f"built {d} ({series_of(meta, content)} series)"
          f"\n  pages 2/3: {words(content['pages'][keys[0]])} / {words(content['pages'][keys[1]])} words"
          f"\n  caption: {cap_words} words before the hashtags"
          f"\n  files: {pre}-*")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
