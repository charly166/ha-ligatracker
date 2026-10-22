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

# Competition logos are not part of the OpenLigaDB data. These are public-domain logos /
# wordmarks on Wikimedia Commons, as direct thumbnail URLs (Special:FilePath is rate-limited
# by Wikimedia and answers HTTP 429). The integration downloads them once and serves them
# through the league's image entity.
_THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/"


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
    "bl1": _THUMB + "1/15/Bundesliga_logo.svg/330px-Bundesliga_logo.svg.png",
    "bl2": _THUMB + "5/58/2._Bundesliga_Wordmark.svg/330px-2._Bundesliga_Wordmark.svg.png",
    "bl3": _THUMB + "e/ec/3._Liga_Wordmark.svg/330px-3._Liga_Wordmark.svg.png",
    "dfb": _THUMB + "2/2a/DFB-Pokal_Wordmark.svg/330px-DFB-Pokal_Wordmark.svg.png",
    "ucl": _THUMB + "0/0a/UEFA_Champions_League_logo.svg/330px-UEFA_Champions_League_logo.svg.png",
    "uel": _THUMB + "1/1b/UEFA_Europa_League_logo_%282024_version%29.svg/330px-UEFA_Europa_League_logo_%282024_version%29.svg.png",
    "uecl": _THUMB + "2/26/UEFA_Conference_League_logo_%282024_version%29.svg/330px-UEFA_Conference_League_logo_%282024_version%29.svg.png",
    "nat": _THUMB + "1/10/DFB-Logo_2025.svg/330px-DFB-Logo_2025.svg.png",
}
