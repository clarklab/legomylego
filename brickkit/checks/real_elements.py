from ..ldraw.library import part_id
from .base import CheckResult, register


@register("real_elements")
def check_real_elements(ctx, cfg) -> CheckResult:
    min_year = cfg.get("min_year", 2016)
    min_sets = cfg.get("min_sets", 3)
    seen, bought = {}, {}
    for p in ctx.placed:
        if getattr(p, "buy", None) is not None:      # a minifig component: checked as sold
            bought.setdefault((p.buy.rb_part, p.buy.color.ldraw), p.buy)
            continue
        seen.setdefault((p.part, p.color.ldraw), p)
    items = []
    n_warn = 0
    hardware, approx = set(), set()

    def check_element(base, rb_or_part, color):
        nonlocal n_warn
        e = ctx.catalog.element(rb_or_part, color)
        if e is None:
            items.append({**base, "severity": "fail",
                          "problem": "LEGO never made this part in this colour",
                          "substitutes": ctx.catalog.substitutes(rb_or_part, color)})
        elif e.last_year < min_year or e.set_count < min_sets:
            n_warn += 1
            items.append({**base, "severity": "warn",
                          "problem": f"rare: in {e.set_count} set(s), last seen "
                                     f"{e.last_year or 'never in a set'}",
                          "element_ids": e.element_ids})

    for (part, _), p in sorted(seen.items()):
        base = {"part": part_id(part), "name": ctx.catalog.part_name(part), "colour": p.color.name}
        if ctx.engine.lib.resolve(part) is None:
            items.append({**base, "severity": "fail", "problem": "not in the LDraw part library"})
            continue
        if ctx.catalog.is_hardware(part):
            hardware.add(part)             # a bought non-LEGO item: on the hardware list
            continue
        if ctx.catalog.is_approximate(part):      # a real part, brickkit's own 3D model
            approx.add(part)
            items.append({**base, "severity": "info",
                          "problem": "LDraw has no model of this part: its 3D shape is "
                                     "brickkit's approximation (data/approximate.json)"})
        elif ctx.engine.lib.is_custom(part):
            items.append({**base, "severity": "fail",
                          "problem": "brickkit stand-in part that is not listed as hardware"})
            continue
        if not ctx.catalog.in_bom(part):
            continue
        check_element(base, part, p.color)
    stand_ins = 0
    for (rb_part, _), c in sorted(bought.items()):
        base = {"part": rb_part, "name": c.name, "colour": c.color.name, "minifig": c.kind,
                "bricklink": c.bl_part}
        for piece in c.pieces:
            if ctx.engine.lib.resolve(piece.part) is None:
                items.append({**base, "severity": "fail",
                              "problem": f"{piece.part} not in the LDraw part library"})
        check_element(base, rb_part, c.color)
        if c.stand_in:
            stand_ins += 1
            items.append({**base, "severity": "info",
                          "problem": "LDraw has no model of this print: drawn plain in its "
                                     "colours (the parts lists name the printed part)"})
        if not c.bl_part:
            items.append({**base, "severity": "info",
                          "problem": "no BrickLink number known (not cross-referenced by "
                                     "LDraw): left out of the BrickLink wanted list"})
    n_fail = sum(1 for i in items if i["severity"] == "fail")
    status = "fail" if n_fail else ("warn" if n_warn else "pass")
    lego = sum(1 for (part, _) in seen if part not in hardware) + len(bought)
    hw = (f"; {len(hardware)} non-LEGO hardware stand-in(s), not checked" if hardware else "")
    figs = (f"; {len(bought)} minifig component(s)"
            + (f", {stand_ins} drawn as stand-ins" if stand_ins else "") if bought else "")
    ap = (f"; {len(approx)} with an approximate 3D model" if approx else "")
    return CheckResult("real_elements", status,
                       f"{lego} part/colour combinations: {n_fail} not real, {n_warn} rare"
                       f"{figs}{ap}{hw}",
                       items, {"combinations": lego, "not_real": n_fail, "rare": n_warn,
                               "hardware": len(hardware), "minifig_components": len(bought),
                               "stand_ins": stand_ins, "approximate": len(approx)})
