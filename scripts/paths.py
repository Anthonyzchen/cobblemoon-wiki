"""Single source of truth for every path the wiki toolchain touches.

The eight legacy patch scripts in the Obsidian vault each hardcoded their own
datapack root, and all eight had drifted to paths that no longer exist. Nothing
in this repo may hardcode a path; import from here.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DOCS = REPO / "docs"
DATA = REPO / "data"
MANIFEST = DATA / "manifest.json"
DEX_JSON = DATA / "dex.json"

GIST_ID = "4d8b86813c879799cd2b33ae0c4db25d"
GIST_FILENAME = "Cobblemon-AdAstra-Pokedex.md"

# --- Pack data (canonical master instance) ---------------------------------
MASTER = Path.home() / "cobblemoon-master"
DATAPACK = MASTER / "saves/Server World/datapacks/cobblemon_adastra_datapack/data"

SPAWN_POOLS = {
    "cobblemon": DATAPACK / "cobblemon/spawn_pool_world",
    "legendary": DATAPACK / "legendary_spawns_atm/spawn_pool_world",
    "paradox": DATAPACK / "paradox_spawns_atm/spawn_pool_world",
    "ultra_beast": DATAPACK / "ultra_beast_spawns_atm/spawn_pool_world",
}
SPECIES_ADDITIONS = DATAPACK / "cobblemon/species_additions"

MODS = MASTER / "mods"
COBBLEMON_JAR = MODS / "Cobblemon-fabric-1.7.3+1.21.1.jar"
MEGA_SHOWDOWN_JAR = MODS / "mega_showdown-fabric-1.8.4+1.7.3+1.21.1.jar"

# `#minecraft:is_*` biome tags ship in the game, not in any mod jar.
VANILLA_JAR = Path.home() / ".gradle/caches/fabric-loom/1.21.1/minecraft-merged.jar"


def require(*paths: Path) -> None:
    """Fail loudly at startup rather than silently producing an empty dex."""
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise SystemExit(
            "[paths] missing required inputs:\n"
            + "\n".join(f"  {p}" for p in missing)
        )
