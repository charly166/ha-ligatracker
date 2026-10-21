<p align="center">
  <img src="HA_Liga_Tracker.png" alt="HA Liga Tracker" width="480">
</p>

# HA Liga Tracker

Fußball-Spielplan, Ergebnisse und Tabellenplätze deiner Lieblingsmannschaften in Home Assistant –
für Bundesliga, 2. Bundesliga, 3. Liga, DFB-Pokal, Champions League, Europa League, Conference
League und die Nationalmannschaft. Datenquelle ist [OpenLigaDB](https://www.openligadb.de)
(kostenlos, ohne API-Key, deutschsprachig).

## Einrichtung

Einstellungen → Geräte & Dienste → Integration hinzufügen → „HA Liga Tracker“.

1. **Mannschaften** wählen (eine oder mehrere). Alle Wettbewerbe, in denen die Mannschaft spielt
   (Liga, Pokal, Europapokal …), werden automatisch berücksichtigt.
2. **Ligen** (optional) wählen: Für jede gewählte Liga entsteht zusätzlich ein Kalender mit
   *allen* Partien dieser Liga.

Beides lässt sich später über „Konfigurieren“ ändern.

## Entitäten

Pro Mannschaft entsteht ein Gerät mit:

| Entität | Beschreibung |
|---|---|
| `calendar.<team>` | Alle Spiele der Mannschaft in allen Wettbewerben. Nach Abpfiff steht das Ergebnis im Titel (z. B. „VfB Stuttgart 1:1 Atletico Madrid“). |
| `sensor.<team>_nachstes_spiel` | Anstoßzeit des nächsten Spiels; Attribute: Gegner, Wettbewerb, Spieltag, Heim/Auswärts. |
| `sensor.<team>_letztes_ergebnis` | Ergebnis des letzten Spiels aus Sicht der Mannschaft (eigene Tore zuerst, z. B. `2:1`); Attribut `result` = win/draw/loss. |
| `sensor.<team>_spielstatus` | `live` während eines Spiels, sonst `idle`; Attribut `score`. |
| `sensor.<team>_tabellenplatz_<wettbewerb>` | Tabellenplatz inkl. Punkte, Tore usw. (Ligen und Ligaphase der Europapokale). |

Pro gewählter Liga entsteht ein Gerät mit einem Kalender (`calendar.<liga>`) aller Partien.

## Hinweise

- OpenLigaDB wird von der Community gepflegt. Ergebnisse stehen im Test wenige Minuten nach
  Abpfiff drin; **ob der Live-Stand während des Spiels aktualisiert wird, hängt von den
  Freiwilligen ab** und ist je Wettbewerb unterschiedlich.
- Während eines Spiels einer gewählten Mannschaft wird minütlich, sonst alle 15 Minuten
  aktualisiert. Liga-Kalender folgen dem 15-Minuten-Takt.
- Die OpenLigaDB-Kürzel sind nicht einheitlich (`ucl`, `uel2026`, …). Die Integration wählt je
  Wettbewerb automatisch das Kürzel mit den meisten Spielen.
