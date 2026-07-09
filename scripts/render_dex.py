#!/usr/bin/env python3
"""Render data/dex.json back to docs/dex/gen-*.md.

Replays each line's `raw`, so the Phase-3 acceptance test (byte-identity against
the parsed source) proves the parse dropped nothing — including the trailing
two-space hard breaks, which are load-bearing and invisible to line counts.

docs/ is the source of truth and dex.json is derived from it, so writing back is
the dangerous direction: rendering a stale dex.json would silently revert hand
edits. Checking is therefore the default, and --write additionally refuses to run
when any target markdown is newer than dex.json.

Usage: render_dex.py            # compare only (default)
       render_dex.py --write    # overwrite docs/dex/*.md from dex.json
"""
import json
import sys

from paths import DEX_JSON, DOCS, require


def render_gen(gen: dict) -> str:
    lines = [gen["heading"], *gen["pre"]]
    for e in gen["entries"]:
        lines.append(e["heading"])
        lines.extend(l["raw"] for l in e["lines"])
        lines.extend(e["trailing"])
    lines.extend(gen["post"])
    return "\n".join(lines)


def main() -> int:
    write = "--write" in sys.argv
    require(DEX_JSON)
    gens = json.loads(DEX_JSON.read_text(encoding="utf-8"))["generations"]

    # A truncated-but-valid dex.json would otherwise render only the generations
    # it happens to contain, leaving the rest stale and the set inconsistent.
    seen = sorted(g["n"] for g in gens)
    if seen != list(range(1, 10)):
        print(f"  FAIL  dex.json has generations {seen}, expected 1..9")
        return 1

    targets = [(g, DOCS / "dex" / f"gen-{g['n']}.md") for g in gens]

    if write:
        stale = [p.name for _, p in targets if p.exists() and p.stat().st_mtime > DEX_JSON.stat().st_mtime]
        if stale:
            print(f"  FAIL  newer than dex.json: {', '.join(stale)}")
            print("        Re-run parse_dex.py first, or these hand edits would be reverted.")
            return 1
        # Render everything before touching disk: a KeyError on gen-8 must not
        # leave gens 1-7 overwritten and 8-9 stale.
        rendered = [(p, render_gen(g)) for g, p in targets]
        for path, out in rendered:
            tmp = path.with_suffix(".md.tmp")
            tmp.write_text(out, encoding="utf-8")
            tmp.replace(path)
        print(f"  wrote {len(rendered)} generation files")
        return 0

    failed = 0
    for gen, path in targets:
        out = render_gen(gen)
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

    print(f"\n  {'ALL 9 GENERATIONS BYTE-IDENTICAL' if not failed else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
