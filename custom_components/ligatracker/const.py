"""Constants for the HA Liga Tracker integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ligatracker"

CONF_TEAMS: Final = "teams"
CONF_LEAGUES: Final = "leagues"
NAME: Final = "HA Liga Tracker"

API_BASE: Final = "https://api.openligadb.de"
ATTRIBUTION: Final = "Daten von OpenLigaDB (openligadb.de)"

# A football match (incl. extra time / penalties) is over well within this window.
MATCH_WINDOW: Final = timedelta(hours=3)
# Calendar events are shown with a fixed length.
EVENT_LENGTH: Final = timedelta(hours=2)
# Start polling faster this long before kick-off.
PRE_KICKOFF: Final = timedelta(minutes=10)

IDLE_INTERVAL: Final = timedelta(minutes=15)
LIVE_INTERVAL: Final = timedelta(seconds=60)
# While a match is live only the affected competitions are refreshed; a full
# refresh (all competitions + tables) still happens at least this often.
FULL_REFRESH_INTERVAL: Final = timedelta(minutes=15)
# Which competitions the selected teams play in is re-discovered this often
# (all curated competitions are scanned, then only the relevant ones are polled).
DISCOVERY_INTERVAL: Final = timedelta(hours=24)

# Competition logos are not part of the OpenLigaDB data. They are public-domain wordmarks /
# logos on Wikimedia Commons that the card loads directly in the browser.
_COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/"


def commons_logo(filename: str, width: int = 256) -> str:
    return f"{_COMMONS}{filename.replace(' ', '_')}?width={width}"


# Curated competitions. OpenLigaDB is community maintained and the shortcuts are
# not consistent between seasons (e.g. "ucl", "ucl2026", "uel2026"), so each
# competition lists candidate shortcuts and the one with the most matches wins.
COMPETITIONS: Final[dict[str, dict]] = {
    "bl1": {"name": "Bundesliga", "shortcuts": ["bl1"], "table": True},
    "bl2": {"name": "2. Bundesliga", "shortcuts": ["bl2"], "table": True},
    "bl3": {"name": "3. Liga", "shortcuts": ["bl3"], "table": True},
    "dfb": {"name": "DFB-Pokal", "shortcuts": ["dfb"], "table": False},
    "ucl": {
        "name": "Champions League",
        "shortcuts": ["ucl", "ucl2026", "ucl24", "ucl2025", "ucl2024"],
        "table": True,
    },
    "uel": {
        "name": "Europa League",
        "shortcuts": ["uel", "uel2026", "uel24", "uel2025"],
        "table": True,
    },
    "uecl": {
        "name": "Conference League",
        "shortcuts": ["uecl", "uecl2026", "uecl2025"],
        "table": True,
    },
    "nat": {
        "name": "Nationalmannschaft",
        "shortcuts": ["DFBN", "DFBNAT2526", "dfb-wm26"],
        "table": False,
    },
}

COMPETITION_LOGOS: Final[dict[str, str]] = {
    "bl1": commons_logo("Bundesliga logo.svg"),
    "bl2": commons_logo("2. Bundesliga Wordmark.svg"),
    "bl3": commons_logo("3. Liga Wordmark.svg"),
    "dfb": commons_logo("DFB-Pokal Wordmark.svg"),
    "ucl": commons_logo("UEFA Champions League logo.svg"),
    "uel": commons_logo("UEFA Europa League logo (2024 version).svg"),
    "uecl": commons_logo("UEFA Conference League logo (2024 version).svg"),
    "nat": commons_logo("DFB-Logo 2025.svg"),
}
