#!/usr/bin/env python3
"""Render data/dex.json back to docs/dex/gen-*.md.

Replays each line's `raw`, so the Phase-3 acceptance test (byte-identity against
the parsed source) proves the parse dropped nothing — including the trailing
two-space hard breaks, which are load-bearing and invisible to line counts.

Usage: render_dex.py [--check]   # --check compares, never writes
"""
import json
import sys

from paths import DEX_JSON, DOCS


def render_gen(gen: dict) -> str:
    lines = [gen["heading"], *gen["pre"]]
    for e in gen["entries"]:
        lines.append(e["heading"])
        lines.extend(l["raw"] for l in e["lines"])
        lines.extend(e["trailing"])
    lines.extend(gen["post"])
    return "\n".join(lines)


def main() -> int:
    check = "--check" in sys.argv
    gens = json.loads(DEX_JSON.read_text(encoding="utf-8"))["generations"]

    failed = 0
    for gen in gens:
        path = DOCS / "dex" / f"gen-{gen['n']}.md"
        out = render_gen(gen)
        if check:
            src = path.read_text(encoding="utf-8")
            if src == out:
                print(f"  PASS  {path.name:<10} {len(out.encode()):>7,} B")
            else:
                failed += 1
                print(f"  FAIL  {path.name}: {len(src.encode()):,} B source vs {len(out.encode()):,} B rendered")
                a, b = src.split("\n"), out.split("\n")
                for i, (x, y) in enumerate(zip(a, b)):
                    if x != y:
                        print(f"        line {i + 1}:\n          source:   {x!r}\n          rendered: {y!r}")
                        break
                else:
                    print(f"        identical until EOF; {abs(len(a) - len(b))} extra line(s)")
        else:
            path.write_text(out, encoding="utf-8")

    if check:
        print(f"\n  {'ALL 9 GENERATIONS BYTE-IDENTICAL' if not failed else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
