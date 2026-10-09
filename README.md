# Bricks
Make LEGO easier than a toaster

Buildable models made only of real LEGO elements. They are designed in Python, checked by
computer, and shipped with parts lists, an instruction booklet, a build video and a 3D viewer
at **[bricks.superfun.games](https://bricks.superfun.games)**.

> Computer-checked; most not yet built with real bricks (the VHS Cassette has been, and it
> works). Every part/colour exists, every
> connection is matched in 3D, nothing overlaps, every step can be built, the model balances
> and the mechanisms sweep through their range without collisions. Clutch, tolerances and
> handling can only be judged with real bricks.

## Models

| Model | Pieces | Size | Works | Rough cost* |
|---|---:|---|---|---|
| [Hamburger](models/hamburger/NOTES.md) | 590 | 12.5 cm across (4.9 in), 9.6 cm tall | a life-size cheeseburger in six separately built layers that click together: sesame bun with a domed top, patty, cheese with hanging corners, lettuce and tomato | $27-$90 |
| [Baby Metroid Lamp](models/baby_metroid/NOTES.md) | 2,903 | 18 cm across, 32 cm tall on its stand | a tap lamp: press it down and the fangs bite and the 3 nuclei light up (Power Functions), press again for off; lifts off its stand | $134-$428 |
| [VHS Cassette](models/vhs_tape/NOTES.md) | 384 | 184 x 102 x 26 mm (real tape: 187 x 103 x 25) | full-length dust flap swings up on Technic pins; both reels turn on red spindles behind two clear windows; black or white (head cleaner) shell | $16-$56 |
| [Ferret](models/ferret/NOTES.md) | 895 | 51 cm nose to tail | head turns on a turntable; sable, albino and cinnamon coats | $37-$117 |
| [Chainsaw Face](models/chainsaw_face/NOTES.md) | 838 | 33.4 cm (13.1 in) tall on his stand, 31.4 cm soles to hair; 12.8 cm chainsaw | posable figure: ball joints at the neck, shoulders, wrists, hips and ankles, ratchet elbows and knees, a waist turntable; swings the chainsaw from overhead down across his hips in both fists; spattered or clean apron | $31-$113 |
| [The Caldwell County Courthouse](models/caldwell_courthouse/NOTES.md) | 6,663 | 44.8 x 44.8 cm base, 65.4 cm tall | four clocks that keep real time (quartz clock inserts, not LEGO, behind SNOT dials); the dome lifts off to set them; clock tower flanked by bell domes, crested corner pavilions; the clockmaster minifigure on the lawn; dark red or reddish brown trim; a 64-piece [mini version](models/caldwell_mini/design.py) for kids | $261-$875 (+ $20-$60 clock inserts) |
| [Nautilus](models/nautilus/NOTES.md) | 7,126 | 106 cm long (42 in), 19 cm across the side keels; 36 cm tall on its 94 x 27 cm sea stand | minifigure scale (the salon windows are LEGO's biggest clear bubbles); the port side of the salon swings up like a gull wing on Nemo's salon and crew; the salon lights up (Power Functions, battery box hidden in the sea); the propeller spins in its guard ring and the rudder swings | $284-$973 |
| [Nautilus Crew](models/nautilus_crew/NOTES.md) | 106 (5 minifigures) | 12.8 x 6.4 cm base, 9.3 cm tall | Captain Nemo, Ned Land, Professor Aronnax, Conseil and a Nautilus diver in a brass deep-sea helmet as real printed minifigures (heads, torsos and legs as sold, listed by their BrickLink numbers) with a harpoon, a spyglass, a magnifying glass, a specimen bottle and a speargun, on a slice of the Nautilus deck before a salon window | $29-$120 |

*Rough range from typical per-part prices (`out/price_estimate.md`), not live market data.
Upload `out/bricklink_wanted.xml` to a BrickLink Wanted List for a real quote.

Each model's `out/` folder holds:

- `<slug>.mpd`: LDraw model; opens in BrickLink Studio, LeoCAD and LDCad.
- `booklet.pdf`: instructions.
- `SLUG-1080x1080.mp4`: build video (every finished video is named model-size).
- `parts.csv`, `bricklink_wanted.xml` and `pick_a_brick.csv`.
- `report.html`: the checks.
- `price_estimate.md`.
- Renders.

Colourways live under `out/variants/<name>/`.

## Quick Bricks from LEGO 11039

Four standalone primary builds from the official Creative Food Friends instructions:
[Birthday Cake](models/birthday_cake/NOTES.md) (20 pieces),
[Watermelon Ice Lolly](models/watermelon_ice_lolly/NOTES.md) (23),
[Avocado](models/avocado/NOTES.md) (23), and [Taco](models/taco/NOTES.md) (23).
Each has its own source-step inventory, parts exports, checks and parsed assembly steps.
[Source reconciliation and verification commands](docs/lego-11039.md) account for all 49
numbered steps and distinguish the 89 primary-build pieces from the set's 61 rebuild pieces.

## brickkit

The engine behind the models is model-agnostic: a new model is a folder under `models/` with
a `model.toml` (palette, colourways, checks, booklet text) and a `design.py`.

```bash
python -m venv .venv && .venv/bin/pip install -e . && .venv/bin/python -m brickkit fetch
.venv/bin/python -m brickkit new my_model --name "My Model"
.venv/bin/python -m brickkit all my_model        # build, check, parts lists (and colourways)
.venv/bin/python -m brickkit booklet my_model    # out/booklet.pdf
.venv/bin/python -m brickkit video my_model      # out/my_model-1080x1080.mp4
.venv/bin/python -m brickkit viewer my_model     # site/models/my_model/
.venv/bin/python tools/site_assets.py            # regenerate site images, pages, sitemap
```

It needs Python 3.12 and Blender 5.2 (headless). For Blender's path, set `BRICKKIT_BLENDER`.
Blender renders take turns on the GPU through a machine-wide lock.

- [docs/new-model.md](docs/new-model.md): the standard way to take in a new small model,
  stage by stage, from pasted instructions or a picture to its page on the site.
  `brickkit new SLUG --quick` scaffolds one and `brickkit status` shows where each one is.
- [AGENTS.md](AGENTS.md): the rules for anyone, or any agent, working in the repo.
- [docs/brickkit-guide.md](docs/brickkit-guide.md): authoring guide (units, model.toml,
  design.py API, mechanisms, electrics, checks, shape helpers).
- [docs/superpowers/specs/](docs/superpowers/specs/): the design spec.

Part geometry comes from the [LDraw](https://www.ldraw.org) library (CC BY 4.0), connection
data from the LDCad shadow library, and part/colour/set data from
[Rebrickable](https://rebrickable.com). LEGO® is a trademark of the LEGO Group, which does
not sponsor, authorize or endorse this project. Metroid is © Nintendo. VHS is a trademark of
JVC KENWOOD Corporation. The Nautilus design is from Walt Disney's 20,000 Leagues Under the
Sea (1954); the model is an unofficial fan model, not affiliated with or endorsed by Disney.
The Nautilus Crew's characters are from Jules Verne's 20,000 Leagues Under the Sea, as in
Walt Disney's 1954 film; an unofficial fan model, not affiliated with or endorsed by Disney.

## Site

`site/` is a static site deployed by Netlify (`netlify.toml`) at bricks.superfun.games.

Shared design tokens and page styles live in `site/assets/css/site.css`; the model viewer
and detail sections use `site/assets/css/model.css`. Inter is served locally from
`site/assets/fonts/` (license included). Edit `site/model.html` for model-page markup,
then run `.venv/bin/python tools/site_assets.py` to refresh the generated `site/m/` pages.
Preview locally with `.venv/bin/python -m http.server 4401 --directory site`.

Quick Bricks has its own gallery at `/quick/` and instruction pages at `/quick/SLUG/`.
Models opt in with `[model] collection = "quick_bricks"`; they stay out of the main
model and video galleries. Edit `site/quick/index.html` for the gallery and
`site/quick-model.html` for the instruction-page template. Refresh both with:

```sh
.venv/bin/python tools/quick_site.py
.venv/bin/python tools/site_assets.py
```

This exports model and step data and copies existing videos, previews, PDFs and parts
files. It does not run Blender or generate videos or booklets. Models without a video
use their existing preview; models without a PDF still have interactive instructions.
Each instruction page starts with the first build step, embeds an existing PDF booklet
when available, and links to Pick a Brick and BrickLink with the model's CSV/XML parts lists.
Use `tools/quick_site.py --index-only` after editing just the page template.

The Bricks mark lives in `site/assets/brand/bricks.svg`, using the supplied SVG path.
The asset script inlines it into page headers and footers and renders the icons, social
previews, and `logo.png` export artwork with resvg and Pillow. Regenerate these assets
after changing the mark; `logo.png` is derived artwork, not the source.
