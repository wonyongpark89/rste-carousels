---
name: RSTE Editors Carousel
description: The RSTE issue cover, carried through seven 1080 × 1350 px LinkedIn slides.
colors:
  cover-orange: "#f6892a"
  cover-ink: "#120c06"
  warm-white: "#f7f5f1"
typography:
  display:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "176px"
    fontWeight: 900
    lineHeight: 0.88
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "96px"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "78px"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.015em"
  title-single:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "104px"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.015em"
  journal:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "58px"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.01em"
  body-lead:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "40px"
    fontWeight: 500
    lineHeight: 1.25
  body-affiliation:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "36px"
    fontWeight: 500
    lineHeight: 1.2
  body:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "36px"
    fontWeight: 400
    lineHeight: 1.25
  url:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "50px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.005em"
  label:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.12em"
  folio:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.06em"
  headline-band:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "80px"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.015em"
  title-compact:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "74px"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.015em"
  body-lead-split:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "44px"
    fontWeight: 500
    lineHeight: 1.25
rounded:
  none: "0px"
spacing:
  margin: "72px"
  title-top: "136px"
  closer-bottom: "136px"
  portrait-gap: "48px"
  interests-top: "28px"
  interests-top-single: "40px"
  closer-rule-gap: "28px"
  affil-top: "18px"
  lines-top: "14px"
  p1-top: "284px"
  p2-top: "780px"
components:
  slide:
    backgroundColor: "{colors.cover-orange}"
    textColor: "{colors.cover-ink}"
    width: "1080px"
    height: "1350px"
    rounded: "{rounded.none}"
  portrait:
    backgroundColor: "{colors.cover-ink}"
    rounded: "{rounded.none}"
    width: "232px"
    height: "290px"
  portrait-single:
    backgroundColor: "{colors.cover-ink}"
    rounded: "{rounded.none}"
    width: "432px"
    height: "540px"
  profile-name:
    textColor: "{colors.cover-ink}"
    typography: "{typography.title}"
  interests-label:
    textColor: "{colors.cover-ink}"
    typography: "{typography.label}"
  interests-lines:
    textColor: "{colors.cover-ink}"
    typography: "{typography.body}"
  folio:
    textColor: "{colors.cover-ink}"
    typography: "{typography.folio}"
  closer:
    textColor: "{colors.cover-ink}"
    typography: "{typography.body-lead}"
    padding: "28px 0 0"
---

# Design System: RSTE Editors Carousel

## Overview

**Creative North Star: "The Issue Cover, Carried Through"**

Every slide is the printed RSTE issue cover extended: a flat orange ground that owns the whole canvas, near-black type set hard against it, and real institutional portraits as the only other colour. It refuses the white contributor page with a coloured accent; orange is never an accent here, it is the paper.

Two voices carry the whole system. Heavy oblique capitals (Archivo 900 italic) speak the cover's voice for slide titles and people's names; plain upright Archivo (400/500) carries everything that is read closely: affiliations, research interests, the closing sentence. Between them, a small tracked 700 capital handles labels and folios. Density is low and phone-first: a 1080 px slide is read at roughly 360–400 px, so nothing that carries information drops below 36 px, and nothing at all drops below 26 px.

The canvas is fixed (1080 × 1350 px), not responsive. Composition is absolute and repeated: the same paired-profile geometry on every two-person slide, portraits alternating edge to edge, so colleagues of equal rank get identical treatment.

**Key Characteristics:**
- Flat orange ground on every slide; ink is the only drawn colour.
- Heavy oblique capitals for titles and names; upright Archivo for reading text.
- Frameless 4:5 rectangular portraits that bleed off the left or right edge.
- One fixed paired-profile geometry, mirrored, shared by all two-person slides.
- Zero radius, zero shadow, zero gradient; a single 4 px ink rule only on cover and closing.

## Colors

Two colours, both from the printed RSTE issue cover; photographs are the only other colour on the artwork.

### Primary
- **Cover Orange** (`cover-orange`): the ground of every slide, edge to edge, sampled from the vol. 44 no. 3 cover.

### Neutral
- **Cover Ink** (`cover-ink`): all type, the 4 px closer rule, the portrait panel fill behind an image, and text selection background. A warm near-black, not pure #000, so it sits on the orange like printed ink. Ink on orange measures about 7.3:1.

- **Warm White** (`warm-white`): the second ground in the mixed-backgrounds version (`carousel-mixed/`) only. Ink on warm white measures about 18:1.

### Named Rules
**The Orange Owns the Ground Rule** (original version, `carousel/`). Orange is the background of every slide, never an accent on white or ink.

**The Two-Colour Rule** (original version). Orange and ink are the entire drawn palette; colour beyond these two comes only from the photographs.

**The Split Field Rule** (mixed-backgrounds version, `carousel-mixed/`, requested by the Editor on 16 October 2026). Each slide divides into one flat orange field and one flat warm white field with a straight, full-width edge. Orange is always a field, never a thin accent. Text keeps at least 48 px clearance from the division.

## Typography

**Display Font:** Archivo 900 italic and 800 italic (with Arial Narrow, sans-serif)
**Body Font:** Archivo 400 and 500 upright (with Arial Narrow, sans-serif)
**Label Font:** Archivo 700 upright, tracked capitals

**Character:** One family in two postures. The heavy oblique capitals are the cover's shout; the upright regular is the quiet reading voice. The contrast is posture and weight, never a second typeface.

All Archivo files are self-hosted under `assets/fonts` (400, 500, 700 upright; 800, 900 italic). Posture and case are not expressible in the token schema: every 900 and 800 role (display, headline, title, title-single, journal) is italic uppercase; label and folio are upright uppercase; all other roles are upright sentence case.

### Hierarchy
- **Display** (900 italic caps, 176px, 0.88): cover and closing titles only ("Meet / the / editors", "Explore / the / journal"), one word per line, top-left at 136 px.
- **Headline** (900 italic caps, 96px, 0.9): the role title on profile slides ("Editors", "Associate editors"), top-left at the margin, stopping 260 px from the right to clear the folio.
- **Title** (900 italic caps, 78px, 0.9; 104px on the single-profile slide): person names, always broken given name / family name across two lines.
- **Journal** (800 italic caps, 58px, 1.0, -0.01em): the full journal title on cover and closing, broken over three lines beneath the display title.
- **Body lead** (500, 40px, 1.25): the closer sentence on cover and closing.
- **Body affiliation** (500, 36px, 1.2): institution and country, directly under the name.
- **Body** (400, 36px, 1.25): research-interest lines.
- **URL** (700, 50px, 1.1): the journal address on the closing slide only.
- **Label** (700, 26px, 0.12em, uppercase): "Research interests" field label.
- **Folio** (700, 26px, 0.06em, uppercase): slide number "NN/07" and the "RSTE" foot mark.

### Named Rules
**The Two Postures Rule.** Oblique heavy capitals for what is announced (slide titles, names, journal title); upright Archivo for what is read (affiliations, interests, sentences). Never set reading text in the oblique, never set a name upright.

**The Shout Spacing Rule.** All 900 italic capitals carry -0.015em letter-spacing and 0.14em word-spacing so multi-word names ("Soo Won", "Radu Bogdan") stay legible as separate words in tight caps.

**The Phone Floor Rule.** 36 px is the floor for anything a reader must read; 26 px is the absolute floor, reserved for the label and folio. Nothing smaller.

## Layout

Fixed 1080 × 1350 px canvas, absolutely positioned. One outer margin of 72 px on all four sides governs titles, text columns, folio and foot.

- **Cover and closing:** display title at top 136 px; journal title at top 662 px; closer block anchored 136 px from the bottom, opened by the 4 px ink rule with 28 px below it; foot row at the bottom margin with "RSTE" left and the folio right.
- **Paired profile slides:** role headline at the top margin; folio top-right at margin + 6 px. Person one starts at 284 px, person two at 780 px. Each person head is the portrait height (290 px); the name and affiliation block sits beside the portrait with a 48 px gap, bottom-aligned (offset -8 px optically). Research interests start 28 px below the head, inset to the 72 px margin.
- **Single profile slide:** the same structure scaled: portrait 432 × 540 px, person at 497 px, name 104 px, interests 40 px below the head.
- **Rhythm:** 18 px name-to-affiliation, 14 px label-to-lines; interest lines are hand-broken at phrase boundaries and never wrap.

### Named Rules
**The Shared Geometry Rule.** Every two-person slide uses identical tops (284 / 780 px), portrait size and gaps. Equal rank means equal pixels; never nudge one colleague larger or higher.

**The Mirror Rule.** On paired slides the first person's portrait bleeds off the left edge and the second's off the right; the text column swaps sides to stay beside the portrait.

## Elevation & Depth

Completely flat. No shadows, no glow, no gradients, no overlap. Depth comes only from the photographs sitting as rectangles on the orange plane; hierarchy is carried by type size and posture.

### Named Rules
**The Printed Plane Rule.** Everything sits on one plane, as ink on a printed cover. If a slide seems to need a shadow to separate something, the composition is wrong.

## Shapes

Rectangles only, zero radius everywhere. Portraits are 4:5 rectangles with no frame, border or keyline, touching the canvas edge on one side. The only line in the system is the 4 px ink rule that opens the closer on cover and closing; profile slides carry no rules.

## Components

### Portrait
Frameless, edge-bleeding, face-matched.
- **Shape:** 4:5 rectangle, 0 radius (232 × 290 px paired; 432 × 540 px single), ink fill behind the image.
- **Placement:** flush to the left edge (first person) or right edge (second person).
- **Crop:** cover-fit, anchored top-centre; a per-portrait zoom (`--z`) and fixed point (`--x`, `--y`) scale every face to a matching size despite very different source crops. Zoom is cropping only; no retouching or background replacement.

### Profile (name + affiliation)
- **Name:** Title role, two lines, given / family.
- **Affiliation:** Body affiliation role, may break to two lines at a natural phrase ("East China Normal / University, China").
- **Position:** beside the portrait, 48 px gap, bottom-aligned with the portrait.

### Research interests
- **Label:** "Research interests" in the Label role.
- **Lines:** Body role, two or three hand-broken lines; phrases on one line are separated by a spaced middle dot (" · "). Lines never wrap.

### Folio and foot
- **Profile slides:** folio "NN/07" alone, top-right.
- **Cover and closing:** foot row at the bottom margin, "RSTE" left, folio right.

### Closer
- **Rule:** 4 px ink top border spanning the margins, 28 px above the text.
- **Text:** Body lead sentence; on the closing slide followed 22 px later by the URL role.

## Do's and Don'ts

### Do:
- **Do** fill every slide edge to edge with Cover Orange and set every mark in Cover Ink.
- **Do** set titles and names in Archivo 900 italic capitals, and affiliations and interests in upright Archivo 400/500.
- **Do** reuse the paired-profile geometry exactly (tops 284 / 780 px, 232 × 290 px portraits, 48 px gap) for every two-person slide.
- **Do** alternate portrait bleed left then right on paired slides.
- **Do** match face scale across portraits with the zoom and fixed-point crop, not by resizing the frame.
- **Do** keep reading text at 36 px or larger and nothing below 26 px.

### Don't:
- **Don't** use gradients, glow, decorative science icons, stock illustrations, rounded cards, or badges and pills.
- **Don't** add rules beyond the single 4 px ink rule on cover and closing.
- **Don't** add a frame, border, radius or shadow to a portrait.
- **Don't** introduce a third colour, a tint of orange, or a white ground.
- **Don't** reproduce the cover's volume, number, date, ISSN or index badge, and don't recreate the Routledge mark.
- **Don't** give one person of a rank more size or prominence than another of the same rank.

## Mixed-backgrounds version

`carousel-mixed/` is a refinement of the same system, exported to `exports/mixed-backgrounds/`. Type, portraits, wording and the mirror arrangement are unchanged. What differs:

- **Cover (slide 1):** orange from 0 to 880 px holds the display title (top 112 px) and journal title (top 624 px). Warm white below holds "Introducing our editorial team" (500, 44 px, 60 px below the division) and the foot row.
- **Profiles (slides 2–6):** a 336 px orange heading band on every profile slide. The role headline (900 italic caps, 80 px) sits on the band's foot, 48 px above the edge, so "Senior associate editor" fits on three lines and one- and two-line roles share its baseline. The folio is top-right in the band. Warm white holds the people: person one at 384 px, person two at 828 px, portraits 200 × 250 px, names 74 px. The single profile keeps the original 432 × 540 px portrait and 104 px name, at 472 px.
- **Closing (slide 7):** warm white from 0 to 880 px holds the title and journal title in the cover's positions. The orange field below holds the invitation (500, 44 px, 60 px below the division), the URL (700, 50 px, 16 px below) and the foot row.
- **Foot row (slides 1 and 7):** the official Taylor & Francis lockup in its original navy #1B127B (`assets/logos/taylor-francis-navy.svg`, 90 px tall; about 6.5:1 on orange) bottom-left; folio bottom-right. No "RSTE" mark. A single-colour ink version is kept as `assets/logos/taylor-francis-ink.svg`. The navy belongs to the lockup only and is never used elsewhere. Never redraw, recolour beyond ink or navy, or distort the lockup.
- **Type tokens for this version:** `headline-band` (role, 80 px), `title-compact` (names, 74 px), `body-lead-split` (cover and closing sentences, 44 px).
- **No ink rule** on cover or closing: the colour division does that job.
