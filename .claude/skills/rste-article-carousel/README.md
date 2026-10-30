# RSTE article carousel generator

Makes a three-page LinkedIn carousel for one article in *Research in Science & Technological Education*:

- page 1: the article details;
- page 2: what the researchers investigated;
- page 3: what they found.

It also writes the post caption. Nothing is published.

## Processing another DOI

Run from your project folder. `SKILL` is this folder, `C:\Users\wp1c21\.claude\skills\rste-article-carousel`.

```
python "%SKILL%\scripts\fetch_metadata.py" 10.1080/02635143.20XX.XXXXXXX
```

This creates a folder in `article-carousels`, named `<first author> - <first six words of the title>` (for example `Mesci - Automated assessment of the nature of`), and prints its path. Every file in it starts with the first author's family name, for example `mesci-caption.txt`.

1. **Confirm the facts.** Open the article on tandfonline.com. Copy each author's first affiliation verbatim into `affiliation_first`, and its house-style form, `Organisation, Country`, into `affiliation_display`. Copy the published abstract into `metadata.json`. Note the source in `sources`, then empty `missing`. The publisher site blocks scripts, so this step is manual (or done by Claude in the browser).
2. **Write the text.** Write `content.json` (see `SKILL.md` for the shape and rules): two sets of 2–4 bullets (40–52 words per page, key phrases marked `==like this==`) and the caption parts.
3. **Build.**
   ```
   python "%SKILL%\scripts\build.py" "article-carousels\<the folder it printed>"
   ```
4. **Review** `<name>-slide-1.png` to `-3.png`, `<name>-carousel.pdf` and `<name>-caption.txt` in that folder. The caption is ready to paste into LinkedIn. It is one paragraph (emoji, the question in Unicode bold serif, the intro with your `**…**` phrases in bold sans, and the DOI link), then a blank line and the hashtags.

In Claude Code you can simply say: *"Make an RSTE carousel for DOI 10.1080/…"*, and the skill runs these steps.

## Series

Set `"series": "archive"` in the content file for a **From the Archive** post. This series uses a light-green theme, a "FROM THE ARCHIVE · <year>" tag, and pages 2 and 3 headed "What did this paper contribute?" and "What has changed, and why it matters" (`pages.contribution`, `pages.today`). Leave `series` out for a new-article post. `SKILL.md` has the rules.

## What each folder holds

| Path | Contents | Changes per article? |
|---|---|---|
| `template/style.css`, `template/fit.js` | layout, type, colour; auto-fit for long titles and bylines | no |
| `template/bullet.svg`, `template/highlight.svg` | hand-drawn star bullet and marigold marker highlight | no |
| `template/bullet-archive.svg`, `template/highlight-archive.svg` | the same in green, for From the Archive | no |
| `assets/` | Archivo fonts (SIL OFL), Taylor & Francis lockup (supplied by the Editor) | no |
| `scripts/` | `fetch_metadata.py`, `build.py` | no |
| `<article_dir>/<name>-metadata.json` | verified facts and source URLs | yes |
| `<article_dir>/<name>-content.json` | the written text for pages 2–3 and the caption | yes |
| `<article_dir>/html/` | generated, editable HTML for that article | generated |

## Safeguards built in

`build.py` stops with a clear message when:

- `metadata.json` still lists missing information, or an affiliation or abstract is unconfirmed;
- a house-style affiliation is not `Organisation, Country`, or uses an organisation or country that is not in the published affiliation;
- a page is outside 40–52 words or 2–4 bullets, or has no highlight or more highlights than bullets;
- the caption's question and intro are outside 30–55 words, there are not 8–12 hashtags, or there are more than two bold phrases;
- text will not fit even at the minimum size;
- the finished PDF does not contain the exact title, every author, every affiliation, the DOI and both page texts.

## Long titles and author lists

The title shrinks from 72 px down to 44 px, and the byline from 42 px down to 26 px, to fit their boxes. If an article has so many authors that even 26 px will not fit, the build stops. Do not shrink further. Ask the Editor whether to list the first authors with "et al." on page 1 (and record that decision in `metadata.json`), or to add a fourth page.

## Requirements

- Python 3.10+, with Pillow and PyMuPDF (`pip install pillow pymupdf`).
- Google Chrome or Microsoft Edge (set `CHROME` to its path if it is not found).
