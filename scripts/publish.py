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

from census import census, diff
from concat import build
from paths import DATA, GIST_FILENAME, GIST_ID

BASELINE = DATA / "census.json"


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    accept = "--accept-census" in argv

    content = build()
    now = census(content)

    for hard in ("yaml_leak", "quad_space_ends"):
        if now[hard]:
            print(f"  FAIL  {hard}={now[hard]}, must be 0. Refusing to publish.")
            return 1

    if BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        changes = diff(base, now)
        # `bytes` and `lines` move with any legitimate content edit.
        material = [c for c in changes if not c.startswith(("bytes:", "lines:"))]
        if material:
            print("  census drift:")
            for c in changes:
                print(f"    {c}")
            if not accept:
                print("\n  Refusing to publish. Re-run with --accept-census if intended.")
                return 1
            print("\n  --accept-census given; proceeding.")
        elif changes:
            print("  census: size changed, structure identical")
        else:
            print("  census: unchanged")
    else:
        print(f"  no baseline; writing {BASELINE.name}")

    if dry_run:
        print(f"  DRY RUN  would publish {now['bytes']:,} bytes, {now['h3']} H3")
        return 0

    payload = json.dumps({"files": {GIST_FILENAME: {"content": content}}})
    proc = subprocess.run(
        ["gh", "api", "-X", "PATCH", f"gists/{GIST_ID}", "--input", "-"],
        input=payload, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"  FAIL  gh api: {proc.stderr.strip()}")
        return proc.returncode

    rev = json.loads(proc.stdout)["history"][0]["version"][:10]
    BASELINE.write_text(json.dumps(now, indent=2) + "\n", encoding="utf-8")
    print(f"  published  revision {rev}  ({now['bytes']:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
