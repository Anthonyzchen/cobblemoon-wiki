#!/usr/bin/env python3
"""Publish docs/ to the public gist.

Guards, in order:
  1. yaml_leak and quad_space_ends must be zero (hard fail, never overridable).
  2. Census must match data/census.json, else --accept-census is required.
  3. --dry-run prints the diff and exits without touching the gist.

The gist is the player-facing URL. Nothing reaches it except through here.

Usage: publish.py [--dry-run] [--accept-census]
"""
import json
import subprocess
import sys

from census import census, diff, frontmatter_files
from concat import build
from paths import DATA, DOCS, GIST_FILENAME, GIST_ID, MANIFEST, require

BASELINE = DATA / "census.json"

# A truncated tail made only of prose (no headings, no hard breaks) moves nothing
# but bytes/lines. Treat a meaningful shrink as drift so it can't ride through as
# an "immaterial" size change.
MAX_SILENT_LINE_LOSS = 5
MAX_SILENT_BYTE_LOSS_PCT = 1.0


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    accept = "--accept-census" in argv

    require(MANIFEST)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(*[DOCS / rel for rel in manifest])

    content = build()
    now = census(content)

    # Hard gates. Never overridable -- each corresponds to a regression that has
    # actually shipped to the public page.
    if leaks := frontmatter_files(DOCS, manifest):
        print(f"  FAIL  frontmatter fence at the top of: {', '.join(leaks)}")
        return 1
    for hard in ("yaml_leak", "quad_space_ends"):
        if now[hard]:
            print(f"  FAIL  {hard}={now[hard]}, must be 0. Refusing to publish.")
            return 1

    if BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))

        if base.get("sha256") == now["sha256"]:
            print("  census: content identical to last publish; nothing to do")
            return 0

        changes = diff(base, now)
        # sha256/bytes/lines move with ANY edit, so they can't themselves signal a
        # regression -- but a large shrink can, and is checked separately below.
        material = [
            c for c in changes if not c.startswith(("sha256:", "bytes:", "lines:"))
        ]
        lost_lines = base.get("lines", 0) - now["lines"]
        lost_pct = 100.0 * (base.get("bytes", 0) - now["bytes"]) / max(base.get("bytes", 1), 1)
        if lost_lines > MAX_SILENT_LINE_LOSS or lost_pct > MAX_SILENT_BYTE_LOSS_PCT:
            material.append(f"shrink: -{lost_lines} lines, -{lost_pct:.2f}% bytes")

        if material:
            print("  census drift:")
            for c in changes:
                print(f"    {c}")
            for c in material:
                if c.startswith("shrink:"):
                    print(f"    {c}")
            if not accept:
                print("\n  Refusing to publish. Re-run with --accept-census if intended.")
                return 1
            print("\n  --accept-census given; proceeding.")
        else:
            delta = now["lines"] - base.get("lines", 0)
            print(f"  census: content changed, structure identical ({delta:+d} lines)")
    else:
        print(f"  no baseline; writing {BASELINE.name}")

    if dry_run:
        print(f"  DRY RUN  would publish {now['bytes']:,} bytes, {now['h3']} H3")
        return 0

    payload = json.dumps({"files": {GIST_FILENAME: {"content": content}}})
    try:
        proc = subprocess.run(
            ["gh", "api", "-X", "PATCH", f"gists/{GIST_ID}", "--input", "-"],
            input=payload, capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("  FAIL  `gh` not found on PATH. Install GitHub CLI and run `gh auth login`.")
        return 1

    if proc.returncode != 0:
        print(f"  FAIL  gh api: {proc.stderr.strip()}")
        return proc.returncode

    # The gist is now live. Persist the baseline BEFORE anything else that can
    # raise, or a bad response body leaves the published content ahead of the
    # baseline forever -- every later run would then report phantom drift.
    try:
        BASELINE.write_text(json.dumps(now, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"  GIST WAS PUBLISHED, but writing {BASELINE} failed: {e}")
        print(f"  Baseline is STALE. Re-run `python3 census.py > {BASELINE}` to resync.")
        return 1

    try:
        rev = json.loads(proc.stdout)["history"][0]["version"][:10]
    except (json.JSONDecodeError, KeyError, IndexError):
        rev = "unknown"
    print(f"  published  revision {rev}  ({now['bytes']:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
