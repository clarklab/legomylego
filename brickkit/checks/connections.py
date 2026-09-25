from collections import Counter

from .base import CheckResult, components, describe, register


@register("connections")
def check_connections(ctx, cfg) -> CheckResult:
    n = len(ctx.placed)
    comps = components(n, [(c.a, c.b) for c in ctx.connections])
    kinds = Counter(c.kind for c in ctx.connections)
    allowed = cfg.get("allow_separate_tags", [])
    items = []
    for comp in comps[1:]:
        tags = {t for i in comp for t in ctx.placed[i].tags}
        if any(t == a for t in tags for a in allowed):
            continue
        items.append({"count": len(comp),
                      "parts": [describe(ctx.placed[i]) for i in comp[:12]],
                      "problem": "not attached to the rest of the model"})
    kind_txt = ", ".join(f"{v} {k}" for k, v in kinds.most_common()) or "none"
    return CheckResult("connections", "fail" if items else "pass",
                       f"{len(ctx.connections)} connections ({kind_txt}); "
                       f"{len(comps)} separate piece(s)", items,
                       {"connections": len(ctx.connections), "by_kind": dict(kinds),
                        "pieces": len(comps)})
