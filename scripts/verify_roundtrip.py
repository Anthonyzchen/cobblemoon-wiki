#!/usr/bin/env python3
"""Phase-2 acceptance test: concat(split(src)) must equal src, byte for byte.

Byte-identity is the whole proof that splitting a 270KB hand-tuned document lost
nothing. Anything less (line counts, heading counts) can pass while trailing
whitespace or a blank line quietly changes -- and trailing whitespace is
load-bearing here (4002 two-space hard breaks).

Usage: verify_roundtrip.py <source.md>
"""
import sys

from concat import build


def main(src_path: str) -> int:
    src = open(src_path, encoding="utf-8").read()
    out = build()

    if src == out:
        print(f"  PASS  round-trip byte-identical ({len(src.encode()):,} bytes)")
        return 0

    print(f"  FAIL  {len(src.encode()):,} B source vs {len(out.encode()):,} B rebuilt")
    a, b = src.split("\n"), out.split("\n")
    print(f"        {len(a):,} lines source vs {len(b):,} lines rebuilt")
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print(f"        first divergence at line {i + 1}:")
            print(f"          source:  {x!r}")
            print(f"          rebuilt: {y!r}")
            break
    else:
        longer, name = (a, "source") if len(a) > len(b) else (b, "rebuilt")
        print(f"        identical until EOF; {name} has {abs(len(a) - len(b))} extra line(s)")
        print(f"          extra: {longer[min(len(a), len(b)):][:3]!r}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1]))
