# RSTE editors carousel — sources and image notes

Not for publication. Nothing here appears on the artwork.

## Content

- Roster, roles and affiliations: https://www.tandfonline.com/journals/crst20/about-this-journal (checked 16 October 2026).
- Wording, research interests and slide order: supplied by Wonyong Park (Editor), 16 October 2026.
- Colour: orange #F6892A sampled from the current issue cover, `photos/crst20.v044.i03.largecover.jpg` (vol. 44 no. 3). The cover's volume, number, date, ISSN and index badge are not reproduced.
- Publisher logo (mixed-backgrounds version, slides 1 and 7): official Taylor & Francis lockup supplied by the Editor as `Downloads/67eb923befa5d-Taylor-Francis.svg` (navy #1B127B). Copied to `assets/logos/` with the viewBox cropped to the artwork. `taylor-francis-ink.svg` is the same artwork with its single fill set to the carousel ink #120C06; `taylor-francis-navy.svg` keeps the original navy. Not redrawn or altered otherwise. Check T&F brand guidance if single-colour black is not an approved variant.
- Fonts: Archivo (SIL Open Font Licence), downloaded from Fontsource via jsDelivr to `assets/fonts/`.

## Portraits

All portraits are real institutional photographs. None is generated, retouched, cut out or reconstructed. In the build they are only cropped and scaled (CSS `object-fit` plus a uniform zoom, `--z`, to even out face scale). Originals are in `photos/`; the build uses the copies in `assets/photos/`.

"Display" is the portrait frame on the slide. "Scale" is source pixels to slide pixels, so above 1× means the photo is enlarged.

| Editor | File | Source px | Display | Scale | Origin |
|---|---|---|---|---|---|
| Chris Harrison | chris_harrison.jpg | 160 × 160 | 232 × 290 | **1.8×** | https://www.kcl.ac.uk/people/christine-harrison |
| Wonyong Park | wonyong_park.jpg | 800 × 799 | 232 × 290 | 0.4× | Supplied by Wonyong Park (`photos/4266-089(413739)-Wonyong_Park - Copy.jpg`) |
| Jack Pun | jack_pun.jpg | 402 × 480 | 432 × 540 | **1.7×** | https://eng.cuhk.edu.hk/staff/jack-pun/ |
| Guopeng Fu | guopeng_fu.jpg | 4912 × 6140 (copy downsampled to 1280 × 1600) | 232 × 290 | 0.3× | https://faculty.ecnu.edu.cn/_s36/fgp/main.psp |
| Soo Won Shim | soo_won_shim.png | 338 × 336 | 232 × 290 | 0.9× (soft source) | https://education.illinoisstate.edu/faculty-staff/profile/?ulid=sshim12 |
| Aik Ling Tan | aik_ling_tan.jpg | 3242 × 4866 (copy downsampled to 1066 × 1600) | 232 × 290 | 0.4× | https://www.ntu.edu.sg/nie/about-us/academic-departments/natural-sciences-and-science-education/faculty |
| Tang Wee Teo | tang_wee_teo.jpg | 848 × 1264 | 232 × 290 | 0.4× | as above |
| Radu Bogdan Toma | radu_bogdan_toma.jpg | 500 × 500 | 232 × 290 | 0.6× | https://investigacion.ubu.es/investigadores/35571/detalle?lang=en |
| Ezgi Yesilyurt | ezgi_yesilyurt.jpg | 400 × 500 | 232 × 290 | 0.8× | https://cehhs.usu.edu/teal/directory/yesilyurt-ezgi |

Portrait-to-name matching follows the filenames and the source notes in `README_SOURCES.txt` (Downloads/RSTE_Editors_Photos_and_Claude_Prompt/rste_carousel_assets/). Please confirm each face before posting.

In the mixed-backgrounds version (`carousel-mixed/`), paired portraits are 200 × 250 px (Chris Harrison about 1.6×). The single portrait stays at 432 × 540 px (Jack Pun about 1.7×).

## Photographs that limit the design

1. **Chris Harrison** (160 × 160). Enlarged about 1.8×; softness is visible at full size and on high-density phone screens. The crop also has almost no space above the hair. This photo is the main reason all paired portraits are kept modest. **Request a larger original.**
2. **Jack Pun** (402 × 480). The single-profile slide shows it at 432 × 540 with a zoom towards the face, an enlargement of about 1.7×. It is acceptable on a phone but soft at full size. A larger original would help.
3. **Soo Won Shim** (338 × 336). It is not enlarged, but the source itself is soft and slightly low-contrast. **Request a sharper original.**
4. **Radu Bogdan Toma**: the University of Burgos logo is partly visible in the background of the source photo. It is left as is, because the brief rules out retouching.
5. **Chris Harrison's face** appears slightly larger in frame than the others. Her source is cropped tightly, and zooming out would need image content that does not exist.

## Replacing a photo

Put the new file in `assets/photos/` under the same name. If its crop differs, adjust `--z` (zoom), `--x` and `--y` (the fixed point: face centre and just above the hair) on that person's `<img>` in `carousel/slide-0N.html`. Then run `python -I export.py`.
