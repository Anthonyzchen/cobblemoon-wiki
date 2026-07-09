#!/usr/bin/env python3
"""Rebuild the monolithic Pokédex markdown from docs/ + manifest.

This is the inverse of split.py and the input to publish.py. It must reproduce
the source byte-for-byte; verify_roundtrip.py enforces that.
"""
import json

from paths import DOCS, MANIFEST


def build() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return "".join((DOCS / rel).read_text(encoding="utf-8") for rel in manifest)


if __name__ == "__main__":
    import sys

    sys.stdout.write(build())
