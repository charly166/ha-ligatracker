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

Per team (one device each): `image` (club logo, also used as entity picture and attribute `team_logo`), `calendar` (all matches, result appended to the title once
finished), `Next match` (timestamp), `Last result` (own goals first, e.g. `2:1`), `Next/Last opponent`, `Next/Last competition`, `Next/Last match home/away`, `Match status`
(`live` / `idle`) and `Table position <competition>` for leagues and league phases.
An `Overview` diagnostic sensor holds all competitions of the team (data source of the card).
Per selected league: one device with a `calendar` of all its matches and a `Matchdays` diagnostic sensor (data source of the league card) and a `League logo` image entity.

## Team card

The integration ships a Lovelace card and loads it automatically (no manual resource needed):

```yaml
type: custom:ligatracker-team-card
entity: sensor.vfb_stuttgart_overview   # the team's Overview sensor
name: VfB Stuttgart                     # optional
```

It shows the team with logo, its league (table position, last and next match with both
teams' logos) and further competitions (cup, European cups) in the same layout. Hard-reload
the browser once after the first update.

## League card

Shows the league logo and name as the header, then all matches of the **next** or **last**
matchday grouped by day, with both teams' logos (results for played matches, kick-off times
otherwise). The league must be selected under "leagues" in the setup.

```yaml
type: custom:ligatracker-league-card
entity: sensor.bundesliga_matchdays   # the league's Matchdays sensor
matchday: next                        # next (default) or last
name: Bundesliga                      # optional
```

League logos: all logos ship with the integration (`custom_components/ligatracker/logos/`, square
PNGs with a margin so the image entity does not crop them) and are served by Home Assistant itself,
without downloading from third-party servers. They are available as the league's image entity,
which the card uses. OpenLigaDB has no league logos.

## Notes

OpenLigaDB is community maintained. Results appear a few minutes after the final whistle; live
scores during a match depend on the volunteers and vary by competition. Polling: every minute
while a selected team is playing, otherwise every 15 minutes.
Some club logos are embedded as images (not URLs) in the OpenLigaDB data (e.g. Arsenal, Aston Villa,
Porto); the integration serves them at `/ligatracker_frontend/team-logo/<id>`.
