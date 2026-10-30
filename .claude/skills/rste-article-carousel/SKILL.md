---
name: rste-article-carousel
description: Make a three-page LinkedIn carousel (PDF, three 1080 × 1350 PNGs, a ready-to-paste caption, metadata) for one article in Research in Science & Technological Education (RSTE, Taylor & Francis), in the RSTE orange/warm-white design. Use when the user gives an RSTE DOI or article link and asks for a carousel, LinkedIn post, social slides or caption for it. Does not publish, post or schedule anything.
---

# RSTE article carousel

Turns one RSTE article DOI into a review-ready LinkedIn carousel. The design lives in `template/` and never changes per article; each article gets its own folder holding only its facts and its written text.

**Never publish.** This skill produces files for the Editor to review. Do not connect to LinkedIn, post, or schedule anything.

## Accuracy rules (these override everything else)

- Facts come only from the published record: title, author list in publication order, each author's **first listed** affiliation, DOI, abstract.
- Write pages 2–3 and the caption only from the published abstract. Infer no findings, numbers, implications, quotations or affiliations it does not state. Keep the authors' qualifications ("argue", "suggest", "in this sample"). Attribute evaluative claims to the authors.
- If the abstract or any affiliation cannot be retrieved reliably, **stop**. Say exactly what is missing and ask the user to paste it or supply the PDF. Never fill a gap with a guess or a secondary source presented as the publisher's.
- Reproduce titles and names exactly as published, including the publisher's spelling (for example "Turkiye").
- **Title house style** (set by the Editor). Titles on the slides are in sentence case:
  - a capital only on the first word, proper nouns (England, Austrian) and acronyms (NOSI, TIMSS);
  - lower case after a colon;
  - written to `title_display`, while `title` keeps the published form.

  The build rejects a `title_display` that differs from the published title by anything other than capitalisation. Leave `title_display` out when the published title is already in sentence case.
- **Affiliation house style** (set by the Editor). On the slides every affiliation reads `Organisation, Country`:
  - the institution's name, or its equivalent for a non-university affiliation, with no department, institute or other subunit;
  - no city;
  - the organisation and country both taken word for word from the published first affiliation;
  - the short form of the organisation's name (for example "Private University of Education", not "…, Diocese of Linz").

  Record the verbatim published string in `affiliation_first` and the house-style form in `affiliation_display`. The build rejects a display form whose organisation or country does not appear in the published string. If the published string names no country, or no clear organisation, stop and ask.

## Workflow

Paths below are relative to this skill folder. Article folders go in the user's working project under `article-carousels/`. Each is named `<first author's family name> - <first six words of the title>`, for example `Mesci - Automated assessment of the nature of`. The fetch script creates and names the folder and prints its path; use that path as `<article_dir>` below. Every file in the folder starts with the first author's family name in lowercase ASCII, for example `mesci-caption.txt`, `mesci-carousel.pdf`, `mesci-slide-1.png`, `mesci-metadata.json` and `mesci-content.json`.

1. **Draft the metadata.**
   ```
   python scripts/fetch_metadata.py <DOI or tandfonline link> [article-carousels]
   ```
   This writes `metadata.json` from Crossref (title, authors, order, ORCID) and OpenAlex (a reconstructed abstract, marked unverified). It lists the fields still to confirm under `"missing"`. If the DOI already has a folder, it stops rather than overwrite confirmed facts (`--force` overrides).

2. **Confirm against the publisher.** Open `https://www.tandfonline.com/doi/full/<DOI>` in the built-in browser; scripted requests are blocked by Cloudflare. Read:
   - each author's first listed affiliation, from the author pop-ups (the page's `.author` elements contain the full affiliation strings);
   - the published abstract, section by section;
   - the keywords.

   Update `<name>-metadata.json`:
   - `authors[].affiliation_first` (verbatim) and `authors[].affiliation_display` (house style);
   - `abstract.text` and `abstract.sections`, with `abstract.source` naming the publisher page and the date;
   - `publisher_keywords`;
   - a `sources` entry for the page.

   Then empty `"missing"`. If the page is paywalled or does not show these fields, do not complete them; ask the user (step 0 of the accuracy rules). Never complete a browser verification or CAPTCHA for the user.

3. **Write `<name>-content.json`** in the article folder (shape below). Check every sentence against the abstract.
   - `pages.investigate`: a list of 2–4 bullets, 40–52 words in total (aim for about 48). Purpose, context and approach in accessible academic English. One bullet per idea.
   - `pages.find`: a list of 2–4 bullets, 40–52 words in total. The principal findings, keeping their qualifications. No exaggeration.
   - Highlights: mark the key phrase of a bullet with `==phrase==`. Use at most one highlight per bullet, and at least one per page. Highlight the claim itself, never a hedge, and never so much that the bullet is all highlight.
   - `caption`:
     - `emoji`: one emoji placed before the question, matched to the topic (for example 🔍 or 🔬). It is the caption's only emoji.
     - `question`: an engaging question related to the article, such as "How do teachers…?" or "Why do students…?". The build sets it in Unicode bold serif; do not mark it.
     - `intro`: one sentence introducing the study, naming the authors. Mark one or two key phrases with `**phrase**`; the build sets them in Unicode bold sans (LinkedIn has no formatting).
     - `hashtags`: 8–12, mixing general and article-specific terms, without `#`.
     - Together, `question` and `intro` should total 30–55 words. The build writes the caption as one paragraph (emoji, bold-serif question, intro, DOI link), then a blank line and the hashtags. There is no opener line and no swipe line. Keep bold to the question and at most two short phrases, because screen readers and search handle Unicode bold poorly.
   - `source_notes`: which abstract sections each text draws on.

4. **Build.**
   ```
   python scripts/build.py <article_dir>
   ```
   The build refuses to run while anything is missing. It also stops if a word count, bullet count or highlight count is out of range, if text overflows its box, or if any title, author, affiliation, DOI or sentence does not appear exactly in the finished PDF.

5. **Inspect.** Open the three PNGs at full size and at phone size (scale to 390 px wide). Check:
   - wrapping, clipping and spacing;
   - authors and affiliations readable;
   - no hyphenated compound split across lines (the build glues them with a word joiner);
   - highlights sit on the lower half of the words and wrap cleanly.

   Fix the content, not the template, unless the template is genuinely wrong for a new case (very long titles or author lists). The template auto-fits titles down to 44 px and bylines down to 26 px. For lists beyond that, see README.

6. **Show the user** the PDF and PNGs for review. Report word counts and anything unverified.

## Series

`content.json` sets `"series"`. Every series uses the same three-page layout and accuracy rules; only the page 1 tag, the two question pages and the colours change.

| Series | Page 1 tag | Page 2 (`pages.<key>`) | Page 3 (`pages.<key>`) | Colours |
|---|---|---|---|---|
| `new` (default) | NEW ARTICLE | What did the researchers investigate? (`investigate`) | What did they find? (`find`) | RSTE orange field, orange stars, marigold marker |
| `archive` | FROM THE ARCHIVE · <issue year> | What did this paper contribute? (`contribution`) | What has changed, and why it matters (`today`) | light green field #C3E4B5, deep-green stars, pale-lime marker |

**From the Archive.**
- Use the issue year (`published_print`), not the online date. Back issues went online years after print.
- Verify every figure on page 2 in the published full text, not only the abstract. Record where each figure came from in `verified_facts` in the metadata.
- Old articles often print no affiliations. If the page shows none, stop and ask the Editor; never infer one from an email address.
- Page 3 and any evaluative sentence ("helped bring students' perspectives…") are the Editor's reflection. Write them from the Editor's text and say so in `source_notes`.
- The caption may be the Editor's own text: put it in `caption.text`. It is used verbatim, with styling only, and must contain the DOI link.

## content.json

```json
{
  "doi": "10.1080/…",
  "pages": {
    "investigate": ["First point with a ==key phrase==.", "Second point.", "Third point."],
    "find": ["…", "…", "…"]
  },
  "caption": {
    "emoji": "🔍",
    "question": "…?",
    "intro": "… compare a **key method** with …",
    "hashtags": ["ScienceEducation", "…"]
  },
  "source_notes": { "investigate": "…", "find": "…", "caption": "…" }
}
```

## Design (do not change per article)

- 1080 × 1350 px pages: RSTE issue-cover orange #F6892A in flat fields, warm white #F7F5F1, ink #120C06. The type is self-hosted Archivo.
- **Page 1:** journal name, a "New article" ink tag and the article title (800 italic) in the orange field. Below, in warm white: authors with affiliation letters (identical house-style affiliations grouped), the DOI, and the official Taylor & Francis lockup in navy.
- **Pages 2–3:** an orange heading band with the question in 900 italic capitals. Below it, 46 px bullets with a hand-drawn orange star (`template/bullet.svg`) and hand-drawn translucent marigold marker highlights (`template/highlight.svg`), then a short citation line.
- No gradients, icons, images of text or generated imagery. Branding is limited to the journal name and the supplied T&F lockup.

The full reference is in `README.md`.
