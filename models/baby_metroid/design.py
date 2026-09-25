"""Baby Metroid: base disc and fangs, skirt, nuclei, dome, and a hover stand that makes it a
tap lamp: press the Metroid down and the fangs bite and the lights toggle on or off.
Front of the model is the diagonal between -X and -Z (the fangs sit on the grid axes)."""
import core
import dome as dome_mod
import nuclei as nuclei_mod
import skirt as skirt_mod
import stand as stand_mod


def build(model):
    model.meta["azimuth_offset"] = -45     # the Metroid faces the -X/-Z diagonal
    model.meta["mechanism_name"] = "Tap"
    model.meta["mechanism_labels"] = ["resting", "pressed"]
    model.meta["hero_open_elevation"] = -6          # from below: the fangs biting
    model.meta["video"] = {"lift": {"exclude_tag": "stand", "height": 80}}
    main = model.main
    disc_cells = core.disc(main)
    core.core(model, main)
    top_cells = skirt_mod.skirt(main, disc_cells)
    nuclei_mod.nuclei(model, main)
    dome_mod.dome(model, main, base_cells=top_cells)
    stand = stand_mod.stand(model)
    main.step("Put the Metroid on its stand")
    main.use(stand, (0, 0, 0), None, tag="stand", insert=(0, 1, 0))
    # the presser meets the box's spring-loaded button, which LDraw models as solid
    model.allow_contact("tube", "battery", "presser pushes the box's on/off button")

