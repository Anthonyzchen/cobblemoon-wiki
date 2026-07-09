#!/usr/bin/env python3
"""Structural census of the dex markdown -- the guard that replaces hand-counting.

Every past regression on this document (duplicated description lines, published
frontmatter, doubled hard-break whitespace) was a change nobody counted. publish.py
refuses to push when the census drifts from data/census.json without --accept-census.

Note on emoji: the rarity markers are SQUARES (U+1F7E9/EA/E6/EA) and the land-spawn
bullet is a CIRCLE (U+1F7E2). They share leading UTF-8 bytes, so grep/awk miscount
them. Always compare decoded str, never bytes.
"""
import hashlib
import json
import re

RARITY = {"🟩": "common", "🟨": "uncommon", "🟦": "rare", "🟪": "ultra_rare"}
METHOD = {"🟢": "land", "🌊": "water_surface", "🐟": "underwater", "🎣": "fishing"}
# Must mirror parse_dex.REALMS. "End" (140 lines) and "Overworld" (76) were missing
# here, so adding or dropping an End/Overworld spawn line was invisible to the guard.
REALMS = ("Verdara", "Moon", "Nether", "Mars", "Venus", "Glacio", "End", "Overworld")

# Obsidian frontmatter that reached the public page once already. An allowlist of
# five keys missed `title:`, `publish:`, `cssclasses:` … so match the fence shape.
FRONTMATTER_RE = re.compile(r"\A---\r?\n[\w-]+:")


def census(text: str) -> dict:
    lines = text.split("\n")
    c = {
        # Content identity. Without it, an equal-length edit (e.g. "level 36" ->
        # "level 63") leaves every structural count untouched and publish reports
        # "census: unchanged" while shipping different content.
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "bytes": len(text.encode()),
        "lines": len(lines),
        "h1": sum(l.startswith("# ") for l in lines),
        "h2": sum(l.startswith("## ") for l in lines),
        "h3": sum(l.startswith("### ") for l in lines),
        "riding_blocks": text.count("🐎"),
        "stat_bullets": sum(l.startswith("• ") for l in lines),
        "use_the_key": text.count("Use the *"),
        "spawns_at_level": text.count("Spawns at level"),
        "hard_breaks": sum(bool(re.search(r"[^ ] {2}$", l)) for l in lines),
        # Load-bearing invariant: a doubled hard break (4 spaces) is invisible to
        # line/token counts but corrupts thousands of lines. It must stay zero.
        "quad_space_ends": sum(bool(re.search(r" {4,}$", l)) for l in lines),
        # Must stay zero: Obsidian frontmatter leaking into the published page.
        "yaml_leak": 1 if FRONTMATTER_RE.match(text) else 0,
    }
    for emoji, name in RARITY.items():
        c[f"rarity_{name}"] = sum(l.startswith(emoji) for l in lines)
    for emoji, name in METHOD.items():
        c[f"method_{name}"] = sum(l.startswith(emoji) for l in lines)
    for realm in REALMS:
        # Trailing space matches parse_dex.classify, which requires " — ".
        c[f"realm_{realm.lower()}"] = sum(l.startswith(f"{realm} — ") for l in lines)
    return c


def frontmatter_files(docs, manifest) -> list[str]:
    """Any docs/ file that itself opens with a frontmatter fence.

    census() only sees the concatenated document, so a fence in the middle of the
    build (i.e. at the top of a non-first chunk) would slip past it.
    """
    return [
        rel
        for rel in manifest
        if FRONTMATTER_RE.match((docs / rel).read_text(encoding="utf-8"))
    ]


def diff(base: dict, new: dict) -> list[str]:
    keys = sorted(set(base) | set(new))
    return [
        f"{k}: {base.get(k, '-')} -> {new.get(k, '-')}"
        for k in keys
        if base.get(k) != new.get(k)
    ]


if __name__ == "__main__":
    from concat import build

    print(json.dumps(census(build()), indent=2))
