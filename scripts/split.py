#!/usr/bin/env python3
"""Split the monolithic Pokédex markdown into docs/ + a manifest.

Chunks are exact line slices of the source and the manifest records their order,
so concat(chunks) is byte-identical to the source by construction. `publish.py`
relies on that; `verify_roundtrip.py` proves it.

Usage: split.py <source.md>
"""
import json
import re
import sys
import unicodedata

from paths import DOCS, MANIFEST

# Heading text -> destination. Anything unmapped gets a slugified fallback so a
# new section can never be silently dropped.
REFERENCE = {
    "What This Pack Changes": "reference/what-this-pack-changes.md",
    "Changed & Non-Craftable Recipes": "reference/recipes.md",
    "Ad Astra — Getting to Space": "reference/space.md",
    "Relic Coins (Currency)": "reference/relic-coins.md",
    "Legendary Index": "reference/legendary-index.md",
    "Form Changes": "reference/form-changes.md",
    "Spawn Rarity": "reference/spawn-rarity.md",
    "Poké Snacks (Spawn Manipulation)": "reference/poke-snacks.md",
    "Riding": "reference/riding.md",
    "Biome Tag Reference": "reference/biome-tags.md",
}
GEN_RE = re.compile(r"^## Generation (\d+) — ")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main(src_path: str) -> None:
    src = open(src_path, encoding="utf-8").read()
    lines = src.split("\n")

    # Boundaries: every H2, plus the `# National Dex` H1. The preamble runs from
    # line 0 to the first boundary.
    bounds = [
        i
        for i, l in enumerate(lines)
        if l.startswith("## ") or l == "# National Dex"
    ]
    if not bounds:
        raise SystemExit("[split] no section boundaries found")

    chunks = [(0, bounds[0], "index.md")]
    in_dex = False
    for n, start in enumerate(bounds):
        end = bounds[n + 1] if n + 1 < len(bounds) else len(lines)
        line = lines[start]

        if line == "# National Dex":
            in_dex, dest = True, "dex/index.md"
        elif (m := GEN_RE.match(line)) :
            dest = f"dex/gen-{m.group(1)}.md"
        else:
            title = line[3:].strip()
            dest = REFERENCE.get(title)
            if dest is None:
                dest = f"reference/{slugify(title)}.md"
                print(f"[split] WARN unmapped section {title!r} -> {dest}")
            # Biome Tag Reference sits after the dex but is reference material.
            if title == "Biome Tag Reference":
                in_dex = False
        chunks.append((start, end, dest))

    manifest = []
    for start, end, dest in chunks:
        # Preserve the source exactly: a chunk is lines[start:end] rejoined, and
        # every chunk but the last is followed by the "\n" that split() consumed.
        body = "\n".join(lines[start:end])
        if end != len(lines):
            body += "\n"
        path = DOCS / dest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        manifest.append(dest)
        print(f"  {dest:<42} {end - start:>5} lines  {len(body.encode()):>7} B")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\n[split] {len(manifest)} files -> {MANIFEST}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
