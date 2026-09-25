from .base import CheckResult, describe, register


@register("collisions")
def check_collisions(ctx, cfg) -> CheckResult:
    pairs = ctx.collide.pairs([(p.part, p.M) for p in ctx.placed])
    items = [{"a": describe(ctx.placed[i]), "b": describe(ctx.placed[j]),
              "problem": "parts overlap"} for i, j in pairs]
    return CheckResult("collisions", "fail" if items else "pass",
                       f"{len(items)} overlapping pair(s) among {len(ctx.placed)} parts", items,
                       {"pairs": len(items)})
