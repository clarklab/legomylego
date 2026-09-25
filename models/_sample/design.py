"""A tiny tower used by the engine tests: a base, two pillar sub-assemblies, a roof."""


def build(model):
    pillar = model.submodel("pillar", "Pillar")
    pillar.place("3003", "body")
    pillar.step()
    pillar.place("3003", "body", (0, -24, 0))

    main = model.main
    main.place("3001", "base")
    main.step("Add the two pillars")
    main.use(pillar, (-20, -24, 0), tag="left")
    main.use(pillar, (20, -24, 0), tag="right")
    main.step("Roof")
    main.place("3001", "roof", (0, -72, 0))
