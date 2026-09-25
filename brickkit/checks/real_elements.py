from ..ldraw.library import part_id
from .base import CheckResult, register


@register("real_elements")
def check_real_elements(ctx, cfg) -> CheckResult:
    min_year = cfg.get("min_year", 2016)
    min_sets = cfg.get("min_sets", 3)
    seen = {}
    for p in ctx.placed:
        seen.setdefault((p.part, p.color.ldraw), p)
    items = []
    n_warn = 0
    for (part, _), p in sorted(seen.items()):
        base = {"part": part_id(part), "name": ctx.catalog.part_name(part), "colour": p.color.name}
        if ctx.engine.lib.resolve(part) is None:
            items.append({**base, "severity": "fail", "problem": "not in the LDraw part library"})
            continue
        if not ctx.catalog.in_bom(part):
            continue
        e = ctx.catalog.element(part, p.color)
        if e is None:
            items.append({**base, "severity": "fail",
                          "problem": "LEGO never made this part in this colour",
                          "substitutes": ctx.catalog.substitutes(part, p.color)})
        elif e.last_year < min_year or e.set_count < min_sets:
            n_warn += 1
            items.append({**base, "severity": "warn",
                          "problem": f"rare: in {e.set_count} set(s), last seen "
                                     f"{e.last_year or 'never in a set'}",
                          "element_ids": e.element_ids})
    n_fail = sum(1 for i in items if i["severity"] == "fail")
    status = "fail" if n_fail else ("warn" if n_warn else "pass")
    return CheckResult("real_elements", status,
                       f"{len(seen)} part/colour combinations: {n_fail} not real, {n_warn} rare",
                       items, {"combinations": len(seen), "not_real": n_fail, "rare": n_warn})
