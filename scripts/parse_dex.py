#!/usr/bin/env python3
"""Parse docs/dex/gen-*.md into data/dex.json — the characterization snapshot.

This freezes six audit passes' worth of hand edits as structured data BEFORE any
generator exists to overwrite them. Phase 4 diffs a pack-data generator against
this file; wherever they disagree, either the generator is wrong or the wiki is.

Fidelity strategy: every line keeps its `raw` text alongside whatever fields we
managed to parse out of it. render_dex.py replays `raw`, so byte-identity never
depends on the classifier being complete — an unrecognized line round-trips as
kind="unknown" instead of silently vanishing.

Usage: parse_dex.py [--report]
"""
import json
import re
import sys

from paths import DEX_JSON, DOCS, require

RARITY = {"🟩": "common", "🟨": "uncommon", "🟦": "rare", "🟪": "ultra_rare"}
METHOD = {"🟢": "land", "🌊": "water_surface", "🐟": "underwater", "🎣": "fishing"}
REALMS = ("Verdara", "Moon", "Nether", "Mars", "Venus", "Glacio", "Overworld", "End", "the End")

HEAD_RE = re.compile(r"^### (.+?) \(#(\d+)(?:\s+(.+?))?\)\s*$")
GEN_RE = re.compile(r"^## Generation (\d+) — (.+)$")
# `\s+` after each label, not ` ` — Rhyperior's Land line reads "Acc  35-55" with a
# double space. A strict single-space match drops that one riding block silently.
STAT_RE = re.compile(
    r"^• (?P<domain>\w+) \((?P<mount>[^)]+)\) —\s+"
    r"Spd\s+(?P<spd>[\d-]+) · Acc\s+(?P<acc>[\d-]+) · Skl\s+(?P<skl>[\d-]+) · "
    r"Jmp\s+(?P<jmp>[\d-]+) · Sta\s+(?P<sta>[\d-]+)\s*$"
)
# "Evolves from X at level N." and "Evolve Cosmog → Cosmoem → Solgaleo (day)."
EVO_RE = re.compile(r"^Evolves? ")
LEVEL_RE = re.compile(r"^Spawns at level ")
# Regional forms are inline dividers, NOT part of the `### Name (#N)` heading:
#   "— Alolan Vulpix (Ice) —"
FORM_RE = re.compile(r"^— (?P<form>.+?) \((?P<types>[A-Za-z/]+)\) —\s*$")
ACQ_PREFIXES = (
    "Use the *", "Or use the *", "Find the *", "Revive a fossil", "Quest reward",
    "Breed ", "Mega Showdown", "Win a ", "Baby — ", "spawns naturally",
    "Not currently obtainable",
)
# Free prose that decorates an entry but carries no structured field.
NOTE_PREFIXES = ("⭐", "The Primal-Reversion")


def _split_top_level(text: str, sep: str) -> list[str]:
    """Split on `sep`, ignoring separators nested inside parentheses.

    Volcanion's biome list is "volcanic biomes (volcano, volcanic peaks, …)" — a
    naive comma split shreds it into 'volcanic biomes (volcano' and 'mantle caves)'.
    """
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [p.strip() for p in out if p.strip()]


def _split_biomes(rest: str) -> tuple[list[str], list[str]]:
    """`biomes · condition · condition` -> (biomes, conditions)."""
    parts = _split_top_level(rest, "·")
    biomes = _split_top_level(parts[0], ",") if parts else []
    return biomes, parts[1:]


def _is_acq(text: str) -> bool:
    return any(text.startswith(p) for p in ACQ_PREFIXES)


def classify(raw: str) -> dict:
    line = raw.rstrip()
    d: dict = {"raw": raw}

    if not line:
        return {**d, "kind": "blank"}

    ch = line[0]
    if ch in RARITY:
        d.update(kind="rarity", tier=RARITY[ch])
        # "🟩 Common spawn:"  or  "🟪 Ultra-rare spawn in oceans."
        body = line[1:].strip()
        if not body.endswith(":"):
            d["inline"] = body
        return d

    if ch in METHOD:
        rest = line[1:].strip()
        # A method marker only denotes a spawn line when it carries the " — biomes"
        # separator. Kyogre uses 🎣 decoratively on a prose acquisition sentence
        # ("🎣 Reel in the *Blue Orb Key* from fishing (~1 in 100,000)…"); treating
        # that as a biome list yields nonsense biomes like "~1 in 100".
        if " — " not in rest:
            kind = "acquisition" if ("Key*" in rest or _is_acq(rest)) else "note"
            return {**d, "kind": kind, "marker": METHOD[ch], "text": rest}
        _, rest = rest.split(" — ", 1)
        d.update(kind="method", method=METHOD[ch])
        d["biomes"], d["conditions"] = _split_biomes(rest)
        return d

    if line.startswith("🐎"):
        return {**d, "kind": "riding_header"}

    if m := STAT_RE.match(line):
        g = m.groupdict()
        return {
            **d, "kind": "riding_stat", "domain": g["domain"], "mount": g["mount"],
            "stats": {k: g[k] for k in ("spd", "acc", "skl", "jmp", "sta")},
        }

    if m := FORM_RE.match(line):
        return {
            **d, "kind": "form_divider", "form": m.group("form"),
            "types": m.group("types").split("/"),
        }

    if EVO_RE.match(line):
        return {**d, "kind": "evolution", "text": line}

    if LEVEL_RE.match(line):
        return {**d, "kind": "spawn_level", "text": line}

    if _is_acq(line):
        return {**d, "kind": "acquisition", "text": line}

    if any(line.startswith(p) for p in NOTE_PREFIXES):
        return {**d, "kind": "note", "text": line}

    # Realm lines: "Verdara — ...", "the End — ...", "Overworld / Verdara — ..."
    if " — " in line:
        head, rest = line.split(" — ", 1)
        names = [p.strip() for p in head.split("/")]
        canon = {"the End": "End"}
        if names and all(n in REALMS for n in names):
            biomes, conds = _split_biomes(rest)
            return {
                **d, "kind": "realm",
                "realm": [canon.get(n, n) for n in names],
                "biomes": biomes, "conditions": conds,
            }

    return {**d, "kind": "unknown", "text": line}


def parse_gen(path) -> dict:
    lines = path.read_text(encoding="utf-8").split("\n")
    m = GEN_RE.match(lines[0])
    if not m:
        raise SystemExit(f"[parse] {path.name}: expected a '## Generation N — Region' heading")

    # Trailing file furniture ('' and '---') belongs to the file, not the last entry.
    end = len(lines)
    while end > 0 and lines[end - 1] in ("", "---"):
        end -= 1
    post, lines = lines[end:], lines[:end]

    heads = [i for i, l in enumerate(lines) if l.startswith("### ")]
    pre = lines[1:heads[0]] if heads else lines[1:]

    entries = []
    for n, start in enumerate(heads):
        stop = heads[n + 1] if n + 1 < len(heads) else len(lines)
        block = lines[start:stop]

        hm = HEAD_RE.match(block[0])
        if not hm:
            raise SystemExit(f"[parse] {path.name}: unparseable heading {block[0]!r}")

        # Separator blanks between entries belong to the entry that precedes them.
        body_end = len(block)
        while body_end > 1 and block[body_end - 1] == "":
            body_end -= 1

        entries.append({
            "dex": int(hm.group(2)),
            "name": hm.group(1),
            "heading": block[0],
            "lines": [classify(l) for l in block[1:body_end]],
            "trailing": block[body_end:],
        })

    return {
        "n": int(m.group(1)), "region": m.group(2), "heading": lines[0],
        "pre": pre, "entries": entries, "post": post,
    }


def main() -> None:
    gen_files = [DOCS / "dex" / f"gen-{i}.md" for i in range(1, 10)]
    require(*gen_files)
    gens = [parse_gen(DOCS / "dex" / f"gen-{i}.md") for i in range(1, 10)]
    DEX_JSON.write_text(json.dumps({"generations": gens}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    entries = [e for g in gens for e in g["entries"]]
    kinds: dict[str, int] = {}
    for e in entries:
        for l in e["lines"]:
            kinds[l["kind"]] = kinds.get(l["kind"], 0) + 1

    print(f"[parse] {len(entries)} entries -> {DEX_JSON}")
    print(f"  dex numbers: {min(e['dex'] for e in entries)}–{max(e['dex'] for e in entries)}, "
          f"{len({e['dex'] for e in entries})} distinct")
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  {k:<14} {v:>5}")

    unknown = [(e["name"], l["raw"]) for e in entries for l in e["lines"] if l["kind"] == "unknown"]
    if unknown:
        print(f"\n  {len(unknown)} unknown lines (round-trip safe, but unstructured):")
        for name, raw in unknown[:15]:
            print(f"    {name:<16} {raw.rstrip()[:78]}")
        if len(unknown) > 15:
            print(f"    … {len(unknown) - 15} more")

    if "--report" in sys.argv:
        first = {}
        for e in entries:
            k = next((l["kind"] for l in e["lines"] if l["kind"] != "blank"), "EMPTY")
            first[k] = first.get(k, 0) + 1
        print("\n  first content line of each entry:")
        for k, v in sorted(first.items(), key=lambda x: -x[1]):
            print(f"    {k:<14} {v:>5}")


if __name__ == "__main__":
    main()
