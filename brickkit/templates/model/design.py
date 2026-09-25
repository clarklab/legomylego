"""{{name}}: describe the model with the builder API. Units: LDU (stud 20, plate 8, brick 24),
-Y is up. Colours are palette roles from model.toml or real colour names."""


def build(model):
    main = model.main
    main.place("3001", "body")
