# Cobblemoon Wiki

Source for the public [Cobblemoon Pokédex wiki](https://gist.github.com/Anthonyzchen/4d8b86813c879799cd2b33ae0c4db25d)
(Cobblemon + Ad Astra, Fabric 1.21.1). The gist is a **build artifact** — never edit it directly.

## Layout

```
docs/index.md              title + intro
docs/reference/*.md        pack reference sections (recipes, riding, biome tags, …)
docs/dex/gen-{1..9}.md     the National Dex, #1–1025
data/manifest.json         file order; concat(manifest) == the published document
data/census.json           structural baseline enforced at publish time
scripts/paths.py           every path in the toolchain, in one place
```

## Editing

Edit files under `docs/`, then:

```sh
cd scripts
python3 publish.py --dry-run    # census check, no network
python3 publish.py              # PATCH the gist
```

`publish.py` refuses to push if:

- **`yaml_leak > 0`** — Obsidian frontmatter reached the page. This shipped once: a
  stray `---` made GitHub render `type: reference tags: [tech…]` as the second heading.
- **`quad_space_ends > 0`** — a hard-break line grew from two trailing spaces to four.
  Invisible to line and token counts; corrupts thousands of lines at once.
- **the structural census drifted** (entry counts, riding blocks, rarity/method/realm
  line counts) without `--accept-census`.

Those are the three regressions that actually happened to this document.

## Gotchas

- **Trailing whitespace is load-bearing.** 4,002 lines end in exactly two spaces
  (markdown hard break); the last line of each entry deliberately does not. Never
  run a global trailing-space strip.
- **`🟢` is not a rarity marker.** Rarity is the squares `🟩🟨🟦🟪`; `🟢` is the
  land-spawn bullet. They share leading UTF-8 bytes, so `grep`/`awk` miscount them —
  compare decoded strings, not bytes.
- **1074 `###` headings ≠ 1074 species.** It's 1025 species + 49 biome-glossary
  categories under `## Biome Tag Reference`.
- Only 892 of the 1025 entries open with a rarity line. The rest open with a realm
  line, `Evolves…`, `Use the *`, `Revive a fossil`, `Quest reward`, or a note — a
  parser keyed on "starts with rarity" silently drops every legendary and fossil.
- The old Obsidian master (`cobblemon_adastra_discord_wiki.md`) is **stale**. This
  repo supersedes it.

## Status

- [x] Repo + split + publish guards (content identical to the live gist)
- [ ] `data/dex.json` — parse the 1025 entries into structured data
- [ ] `scripts/gen_dex.py` — regenerate the dex from pack data, diffed against the parse
- [ ] Astro Starlight site
