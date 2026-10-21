<p align="center">
  <img src="HA_Liga_Tracker.png" alt="HA Liga Tracker" width="480">
</p>

# HA Liga Tracker

Football fixtures, results and table positions for your favourite teams – Bundesliga, 2.
Bundesliga, 3. Liga, DFB-Pokal, Champions League, Europa League, Conference League and the
German national team. Data comes from [OpenLigaDB](https://www.openligadb.de) (free, no API key).
Deutsche Version: [README.de.md](README.de.md).

## Setup

Settings → Devices & services → Add integration → "HA Liga Tracker".

1. Pick one or more **teams**. All competitions a team plays in are covered automatically.
2. Optionally pick **leagues**: each gets its own calendar with *all* matches of that league.

Both can be changed later via *Configure*.

## Entities

Per team (one device each): `calendar` (all matches, result appended to the title once
finished), `Next match` (timestamp), `Last result` (own goals first, e.g. `2:1`), `Match status`
(`live` / `idle`) and `Table position <competition>` for leagues and league phases.
Per selected league: one device with a `calendar` of all its matches.

## Notes

OpenLigaDB is community maintained. Results appear a few minutes after the final whistle; live
scores during a match depend on the volunteers and vary by competition. Polling: every minute
while a selected team is playing, otherwise every 15 minutes.
