"""Config flow and entity tests (pytest-homeassistant-custom-component)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ligatracker.const import CONF_LEAGUES, CONF_TEAMS, DOMAIN
from custom_components.ligatracker.model import TableRow


@pytest.fixture(autouse=True)
def _auto_enable(enable_custom_integrations):
    return


def _team(tid: int, name: str) -> dict:
    icon = "https://example.com/vfb.png" if tid == 16 else "data:image/png;base64,AAAA"
    return {"teamId": tid, "teamName": name, "shortName": name, "teamIconUrl": icon}


def _match(mid: int, kickoff: datetime, t1, t2, finished: bool, score=None) -> dict:
    results = []
    if score:
        results = [
            {"resultTypeID": 1, "resultOrderID": 1, "pointsTeam1": 0, "pointsTeam2": 0},
            {"resultTypeID": 2, "resultOrderID": 2, "pointsTeam1": score[0], "pointsTeam2": score[1]},
        ]
    return {
        "matchID": mid,
        "matchDateTimeUTC": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "group": {"groupName": f"{mid}. Spieltag", "groupOrderID": mid},
        "team1": t1,
        "team2": t2,
        "matchIsFinished": finished,
        "matchResults": results,
        "location": None,
    }


def _raw_matches() -> list[dict]:
    now = datetime.now(timezone.utc)
    vfb, bmg = _team(16, "VfB Stuttgart"), _team(87, "Borussia Mönchengladbach")
    return [
        _match(1, now - timedelta(days=6), bmg, vfb, True, (1, 2)),
        _match(2, now + timedelta(days=2), vfb, bmg, False),
    ]


async def _get_matches(self, shortcut: str, season: int) -> list[dict]:
    """Only the Bundesliga has matches; everything else is empty."""
    return _raw_matches() if shortcut == "bl1" else []


def _table() -> list[TableRow]:
    return [TableRow(16, "VfB Stuttgart", 3, 12, 6, 4, 0, 2, 9, 5, 4)]


async def test_config_flow(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.ligatracker.api.OpenLigaDBClient.get_matches",
        _get_matches,
    ), patch("custom_components.ligatracker.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TEAMS: ["16"]}
        )
        assert result["step_id"] == "leagues"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LEAGUES: ["bl1"]}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HA Liga Tracker"
    assert result["data"] == {CONF_TEAMS: {"16": "VfB Stuttgart"}, CONF_LEAGUES: ["bl1"]}


async def test_entities(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        version=2,
        data={CONF_TEAMS: {"16": "VfB Stuttgart"}, CONF_LEAGUES: ["bl1"]},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.ligatracker.api.OpenLigaDBClient.get_matches",
        _get_matches,
    ), patch(
        "custom_components.ligatracker.api.OpenLigaDBClient.get_table",
        return_value=_table(),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    last = hass.states.get("sensor.vfb_stuttgart_last_result")
    assert last is not None and last.state == "2:1"  # Stuttgart won away: own goals first
    assert last.attributes["result"] == "win"
    assert last.attributes["opponent_logo"] is None  # data: URIs are dropped

    nxt = hass.states.get("sensor.vfb_stuttgart_next_match")
    assert nxt is not None and nxt.state != "unknown"
    assert nxt.attributes["home"] is True

    assert hass.states.get("sensor.vfb_stuttgart_last_opponent").state == "Borussia Mönchengladbach"
    assert hass.states.get("sensor.vfb_stuttgart_last_competition").state == "Bundesliga"
    assert hass.states.get("sensor.vfb_stuttgart_next_opponent").state == "Borussia Mönchengladbach"
    assert hass.states.get("sensor.vfb_stuttgart_next_competition").state == "Bundesliga"

    assert hass.states.get("sensor.vfb_stuttgart_next_match_home_away").state == "home"
    assert hass.states.get("sensor.vfb_stuttgart_last_match_home_away").state == "away"

    assert hass.states.get("sensor.vfb_stuttgart_match_status").state == "idle"
    assert hass.states.get("sensor.vfb_stuttgart_table_position_bundesliga").state == "3"
    assert hass.states.get("calendar.vfb_stuttgart") is not None
    assert last.attributes["team_logo"] == "https://example.com/vfb.png"
    assert last.attributes["entity_picture"] == "https://example.com/vfb.png"
    logo = hass.states.get("image.vfb_stuttgart_logo")
    assert logo is not None and logo.state != "unavailable"
    assert hass.states.get("calendar.bundesliga") is not None  # league calendar

    overview = hass.states.get("sensor.vfb_stuttgart_overview")
    assert overview is not None and overview.state == "1"
    assert overview.attributes["team"]["logo"] == "https://example.com/vfb.png"
    (comp,) = overview.attributes["competitions"]
    assert comp["key"] == "bl1" and comp["league"] is True
    assert comp["table"]["position"] == 3
    assert comp["last"]["score"] == [1, 2] and comp["last"]["result"] == "win"
    assert comp["last"]["team_is_home"] is False
    assert comp["next"]["home"] == "VfB Stuttgart" and comp["next"]["score"] is None
    assert comp["live"] is None

    league = hass.states.get("sensor.bundesliga_matchdays")
    assert league is not None and league.state == "2. Spieltag"  # next matchday
    assert league.attributes["competition"]["name"] == "Bundesliga"
    assert league.attributes["competition"]["logo"].startswith("https://commons.wikimedia.org/")
    assert league.attributes["last"]["name"] == "1. Spieltag"
    (played,) = league.attributes["last"]["matches"]
    assert played["score"] == [1, 2] and played["finished"] is True
    (upcoming,) = league.attributes["next"]["matches"]
    assert upcoming["score"] is None and upcoming["finished"] is False


async def test_deselected_team_and_league_are_removed(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        version=2,
        data={
            CONF_TEAMS: {"16": "VfB Stuttgart", "87": "Borussia Mönchengladbach"},
            CONF_LEAGUES: ["bl1"],
        },
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.ligatracker.api.OpenLigaDBClient.get_matches", _get_matches
    ), patch(
        "custom_components.ligatracker.api.OpenLigaDBClient.get_table", return_value=_table()
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("calendar.borussia_monchengladbach") is not None
        assert hass.states.get("calendar.bundesliga") is not None

        hass.config_entries.async_update_entry(
            entry, data={CONF_TEAMS: {"16": "VfB Stuttgart"}, CONF_LEAGUES: []}
        )
        await hass.async_block_till_done()

    assert hass.states.get("calendar.vfb_stuttgart") is not None
    assert hass.states.get("calendar.borussia_monchengladbach") is None
    assert hass.states.get("calendar.bundesliga") is None
    assert hass.states.get("sensor.borussia_monchengladbach_next_match") is None
