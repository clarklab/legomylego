# Working in this repo

Buildable LEGO models, checked by the `brickkit` engine, with their parts lists, instruction
booklets, videos and a static site (`site/`, deployed by Netlify from `main` to
bricks.superfun.games).

## Where to look

- **Adding a model:** [docs/new-model.md](docs/new-model.md) is the standard, stage by stage.
  `brickkit new SLUG --quick` scaffolds one; `brickkit status` shows where each model is and
  what to do next.
- **The engine:** [docs/brickkit-guide.md](docs/brickkit-guide.md) (commands, model.toml,
  design.py, checks, videos).
- **Setup and the site:** [README.md](README.md). Use `.venv/bin/python`.

## Rules

- **Claim a model before you work on it:** `brickkit claim SLUG --as NAME`, and
  `brickkit release SLUG --as NAME` when you stop. If someone else has it, pick another.
  `brickkit status` shows who has what.
- **One Blender render at a time.** Renders take turns on one GPU through a machine-wide
  lock. Go through the `brickkit` commands, or wrap a Blender launch of your own in
  `brickkit.render.scene.blender_slot()`. Starting Blender outside the lock while a render
  runs has crashed the GPU and killed that render.
- **Do not edit the render scripts while a video renders:** `brickkit/render/blender_quick.py`,
  `quick_sets.py`, `blender_scene.py`, `blender_animate.py`, `blender_cold_open.py`. Each
  chunk of frames loads them from disk, and a changed file throws the frames away.
- **Quick Bricks videos must build for real.** No part passes through another, and each
  lands on something. `brickkit quick` prints a `quick:` line for anything that does not;
  fix it before rendering. `tests/test_quick.py::test_quick_builds_for_real` holds every
  Quick Bricks model to it.
- **The repo is public.** Never commit LEGO's own instruction PDFs or zips of them
  (`docs/references/` ignores them). Credit the designer of a model that is not ours.
- **Secrets stay out.** API keys live in `~/.config/brickkit/*.env`. Never print, log or
  commit them.
- **Publish only when the owner says so.** That covers pushing to `main`, tagging a model
  `quick_bricks`, and anything else that changes the live site.
- **Never buy anything** or put anything in a cart. Parts lists are files to upload by hand.
- **Other sessions may share this checkout.** Commit only the files you changed, by name.
  Leave files you do not recognise alone.
- **Before saying something is done,** run the tests (`.venv/bin/python -m pytest -q`) and
  look at what you made: the report, the booklet's pages, the video's frames.
