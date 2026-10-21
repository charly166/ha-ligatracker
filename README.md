# Liga Tracker for Home Assistant

Football fixtures, results and table positions for your favourite teams – Bundesliga, 2.
Bundesliga, 3. Liga, DFB-Pokal, Champions League, Europa League, Conference League and the
German national team. Data comes from [OpenLigaDB](https://www.openligadb.de) (free, no API key).
Deutsche Version: [README.de.md](README.de.md).

## Setup

Settings → Devices & services → Add integration → "Liga Tracker". Pick one or more
**competitions**, then one or more **teams**. Both can be changed later via *Configure*.

## Entities (per team, one device each)

- `calendar` – all matches in the selected competitions; the result is appended to the title
  once a match is finished.
- `Next match` (timestamp), `Last result` (own goals first, e.g. `2:1`), `Match status`
  (`live` / `idle`), and `Table position <competition>` for leagues and league phases.

## Notes

OpenLigaDB is community maintained. Results appear a few minutes after the final whistle; live
scores during a match depend on the volunteers and vary by competition. Polling: every minute
while a selected team is playing, otherwise every 15 minutes.
