"""Draft metadata.json for one RSTE article from open scholarly APIs.

    python fetch_metadata.py <DOI> [parent_dir] [--provisional]

parent_dir defaults to ./article-carousels. The article gets its own folder there, named
"<first author's family name> - <first six words of the title>", for example
"Mesci - Automated assessment of the nature of". The script prints the folder it used.

Sources, in order of authority:
  1. Crossref   - title, author order, ORCIDs, short affiliations, dates.
  2. OpenAlex   - abstract (reconstructed from an inverted index) and keywords.
The publisher page (tandfonline.com) is the authority for the full first affiliation
and the published abstract, but it blocks scripted requests. The draft therefore lists
those fields under "missing" until someone confirms them from the publisher page (or
the article PDF) and records the source. build.py refuses to render while "missing"
is not empty.

--provisional (scheduled cloud runs, where the publisher page cannot be opened) completes the
draft from the open sources instead: the OpenAlex abstract (section headings restored), the
OpenAlex keywords and the Crossref affiliation (organisation, place) for each author. Every
such field is listed under "provisional" in metadata.json, so build.py renders the draft and
the pipeline shows the Editor a warning to compare it with the publisher page before approving.
It exits with code 3, writing nothing, if OpenAlex has no abstract yet (new articles often
take days to be indexed) or Crossref has no affiliation for an author; the article is retried
on a later run.
"""
import datetime, json, pathlib, re, sys, unicodedata, urllib.parse, urllib.request

UA = "RSTE-article-carousel/1.0 (mailto:editor-rste@example.invalid)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


HEADINGS = ("Design and Methods", "Design/methodology/approach", "Methods", "Method", "Background", "Purpose",
            "Aims", "Aim", "Context", "Rationale", "Sample", "Design", "Results", "Findings",
            "Conclusions", "Conclusion", "Implications")


def restore_sections(text):
    """OpenAlex runs the structured headings into the text ('...credibility.Purpose This study').
    Put 'Heading: ' back and return (text, sections); text is returned unchanged unless 3+ headings are found."""
    pat = re.compile(r"(?:(?<=^)|(?<=[.!?)\u201d\"']))(" + "|".join(re.escape(h) for h in HEADINGS) + r")(?=:?\s+[A-Z\u201c\"(])")
    hits = list(pat.finditer(text))
    if len(hits) < 3 or hits[0].start() != 0:
        return text, []
    sections = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        body = text[m.end():end].lstrip(": ").strip()
        sections.append({"heading": m.group(1), "text": body})
    return " ".join(f"{x['heading']}: {x['text']}" for x in sections), sections


def folder_name(authors, title):
    """'<family name> - <first six words of title>', safe on Windows, macOS and Linux."""
    who = (authors[0].get("family") or authors[0]["name"]) if authors else "Unknown author"
    words = re.sub(r"<[^>]+>", "", title or "Untitled").split()[:6]
    name = f"{who} - {' '.join(words)}"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    return name.rstrip(" .,;-")


def file_prefix(authors):
    """First author's family name in plain lowercase ASCII ('Mesci' -> 'mesci'); every file starts with it."""
    a = authors[0] if authors else {"name": "article"}
    name = a.get("family") or a["name"].split()[-1]
    name = re.sub("[\u2010-\u2015\u2212]", "-", name)   # typographic hyphens and dashes count as hyphens
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "article"


def existing_folder(parent, doi):
    for m in parent.glob("*/*metadata.json"):
        try:
            if json.loads(m.read_text(encoding="utf-8")).get("doi", "").lower() == doi.lower():
                return m.parent
        except (ValueError, OSError):
            pass
    return None


def main(doi, parent_dir="article-carousels", provisional=False):
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:|https?://www\.tandfonline\.com/doi/(full|abs)/)", "", doi.strip())
    parent = pathlib.Path(parent_dir)
    parent.mkdir(parents=True, exist_ok=True)
    found = existing_folder(parent, doi)
    if found and "--force" not in sys.argv:
        sys.exit(f"{doi} already has a folder: {found}\n"
                 "Its metadata.json may hold confirmed facts; "
                 "rerun with --force only if you mean to overwrite it.")
    today = datetime.date.today().isoformat()
    sources, missing = [], []

    cr_url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    cr = get(cr_url)["message"]
    sources.append({"what": "title, authors, author order, ORCID, short affiliations, dates", "url": cr_url, "retrieved": today})

    def date(key):
        parts = (cr.get(key) or {}).get("date-parts", [[None]])[0]
        return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p) or None

    authors = []
    for a in cr.get("author", []):
        given, family = a.get("given", ""), a.get("family", "")
        affs = [x.get("name") for x in a.get("affiliation", []) if x.get("name")]
        authors.append({
            "name": f"{given} {family}".strip(),
            "given": given, "family": family,
            "orcid": a.get("ORCID"),
            "affiliation_crossref": affs[0] if affs else None,
            "affiliation_first": None,          # full published form, from the publisher page
            "affiliation_display": None,        # RSTE house style for slides: "Organisation, Country"
        })
    if not authors:
        missing.append("authors")

    abstract = {"text": None, "source": None}
    keywords = []
    try:
        oa_url = "https://api.openalex.org/works/doi:" + doi
        oa = get(oa_url)
        inv = oa.get("abstract_inverted_index")
        if inv:
            pos = {p: w for w, ps in inv.items() for p in ps}
            text, sections = restore_sections(" ".join(pos[i] for i in sorted(pos)))
            abstract = {"text": text, "source": oa_url + " (reconstructed; unverified)"}
            if sections:
                abstract["sections"] = sections
        keywords = [k["display_name"] for k in oa.get("keywords", [])]
        sources.append({"what": "abstract (reconstructed), keywords", "url": oa_url, "retrieved": today})
    except Exception as e:  # OpenAlex is optional
        sources.append({"what": f"OpenAlex unavailable: {e}", "url": None, "retrieved": today})

    provisional_note = None
    if provisional:
        gaps = []
        if not abstract["text"]:
            gaps.append("OpenAlex has no abstract for this DOI yet")
        for a, c in zip(authors, cr.get("author", [])):
            aff = next((x for x in c.get("affiliation", []) if x.get("name")), None)
            place = (aff or {}).get("place") or []
            country = place[0].rsplit(",", 1)[-1].strip() if place else ""
            if not aff or not country:
                gaps.append(f"Crossref has no affiliation with a place for {a['name']}")
                continue
            a["affiliation_first"] = f"{aff['name']}, {place[0]}"
            a["affiliation_display"] = f"{aff['name']}, {country}"
        if gaps:
            print("provisional draft not possible:", *("  - " + g for g in gaps), sep="\n")
            sys.exit(3)
        provisional_note = {
            "created": today,
            "unverified": ["abstract (OpenAlex reconstruction, headings restored)",
                           "affiliation_first and affiliation_display (Crossref short form, not the full published affiliation)",
                           "keywords (OpenAlex; no publisher keywords)"],
            "action": "Compare the abstract and affiliations with the tandfonline page before approving; "
                      "if they differ, 'Revise' with the published wording.",
        }
        missing = [m for m in missing if m == "authors"]
    else:
        missing += [
            "affiliation_first for every author (confirm on the publisher page or PDF)",
            "affiliation_display for every author (house style: Organisation, Country)",
            "abstract (confirm the published abstract on the publisher page or PDF)",
        ]
    meta = {
        "doi": doi,
        "doi_url": "https://doi.org/" + doi,
        "publisher_url": (cr.get("resource") or {}).get("primary", {}).get("URL"),
        "journal": (cr.get("container-title") or [None])[0],
        "title": (cr.get("title") or [None])[0],
        "type": cr.get("type"),
        "published_online": date("published-online") or date("published"),
        "published_print": date("published-print"),
        "volume": cr.get("volume"), "issue": cr.get("issue"), "pages": cr.get("page"),
        "authors": authors,
        "abstract": abstract,
        "publisher_keywords": [],
        "openalex_keywords": keywords,
        "sources": sources,
        "missing": missing,
    }
    if provisional_note:
        meta["provisional"] = provisional_note
    if meta["journal"]:
        meta["journal"] = meta["journal"].replace("&amp;", "&")
    if meta["journal"] != "Research in Science & Technological Education":
        missing.insert(0, f"journal check: Crossref says {meta['journal']!r}")
    out = found or parent / folder_name(authors, meta["title"])
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{file_prefix(authors)}-metadata.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"article folder: {out}")
    print(f"wrote {path}")
    print("still missing:" if missing else "complete", *("  - " + m for m in missing), sep="\n")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in ("--force", "--provisional")]
    if not 1 <= len(args) <= 2:
        sys.exit(__doc__)
    main(*args, provisional="--provisional" in sys.argv)
