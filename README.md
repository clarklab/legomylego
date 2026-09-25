# legomylego
Make LEGO easier than a toaster

Buildable models made only of real LEGO elements. They are designed in Python, checked by
computer, and shipped with parts lists, an instruction booklet, a build video and a 3D viewer
at **[lego.superfun.games](https://lego.superfun.games)**.

> Computer-checked, not yet built with real bricks. Every part/colour exists, every
> connection is matched in 3D, nothing overlaps, every step can be built, the model balances
> and the mechanisms sweep through their range without collisions. Clutch, tolerances and
> handling can only be judged with real bricks.

## Models

| Model | Pieces | Size | Works | Rough cost* |
|---|---:|---|---|---|
| [Baby Metroid](models/baby_metroid/NOTES.md) | 2,681 | 18 cm across, 29 cm tall on its stand | fangs open and close from a knob (worm drive); 3 nuclei lit by Power Functions LEDs; lifts off a hover stand | $124-$396 |
| [VHS Cassette](models/vhs_tape/NOTES.md) | 348 | 184 x 104 x 26 mm (real tape: 187 x 103 x 25) | dust door flips up on click hinges; both reels spin | $12-$43 |
| [Ferret](models/ferret/NOTES.md) | 895 | 51 cm nose to tail | head turns on a turntable; sable, albino and cinnamon coats | $37-$117 |

*Rough range from typical per-part prices (`out/price_estimate.md`), not live market data.
Upload `out/bricklink_wanted.xml` to a BrickLink Wanted List for a real quote.

Each model's `out/` folder holds:

- `<slug>.mpd`: LDraw model; opens in BrickLink Studio, LeoCAD and LDCad.
- `booklet.pdf`: instructions.
- `video.mp4`: build video.
- `parts.csv`, `bricklink_wanted.xml` and `pick_a_brick.csv`.
- `report.html`: the checks.
- `price_estimate.md`.
- Renders.

Colourways live under `out/variants/<name>/`.

## brickkit

The engine behind the models is model-agnostic: a new model is a folder under `models/` with
a `model.toml` (palette, colourways, checks, booklet text) and a `design.py`.

```bash
python -m venv .venv && .venv/bin/pip install -e . && .venv/bin/python -m brickkit fetch
.venv/bin/python -m brickkit new my_model --name "My Model"
.venv/bin/python -m brickkit all my_model        # build, check, parts lists (and colourways)
.venv/bin/python -m brickkit booklet my_model    # out/booklet.pdf
.venv/bin/python -m brickkit video my_model      # out/video.mp4
.venv/bin/python -m brickkit viewer my_model     # site/models/my_model/
.venv/bin/python tools/site_assets.py            # regenerate site images, pages, sitemap
```

It needs Python 3.12 and Blender 5.2 (headless). For Blender's path, set `BRICKKIT_BLENDER`.
Blender renders take turns on the GPU through a machine-wide lock.

- [docs/brickkit-guide.md](docs/brickkit-guide.md): authoring guide (units, model.toml,
  design.py API, mechanisms, electrics, checks, shape helpers).
- [docs/superpowers/specs/](docs/superpowers/specs/): the design spec.

Part geometry comes from the [LDraw](https://www.ldraw.org) library (CC BY 4.0), connection
data from the LDCad shadow library, and part/colour/set data from
[Rebrickable](https://rebrickable.com). LEGO® is a trademark of the LEGO Group, which does
not sponsor, authorize or endorse this project. Metroid is © Nintendo. VHS is a trademark of
JVC KENWOOD Corporation.

## Site

`site/` is a static site deployed by Netlify (`netlify.toml`) at lego.superfun.games.
