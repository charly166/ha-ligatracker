"""Sensor platform: next match, last result, live status and table position."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .const import COMPETITIONS
from .coordinator import LigaTrackerCoordinator
from .entity import TeamEntity
from .model import Match, last_match, live_match, next_match


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LigaTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for team_id in coordinator.teams:
        entities += [
            NextMatchSensor(coordinator, team_id),
            LastMatchSensor(coordinator, team_id),
            MatchStatusSensor(coordinator, team_id),
        ]
    async_add_entities(entities)

    # Table sensors depend on which tables actually contain the team, so they are
    # added as soon as the data shows up (e.g. after the league phase starts).
    known: set[tuple[int, str]] = set()

    @callback
    def _add_tables() -> None:
        new: list[SensorEntity] = []
        for key, rows in (coordinator.data.tables if coordinator.data else {}).items():
            for row in rows:
                if row.team_id in coordinator.teams and (row.team_id, key) not in known:
                    known.add((row.team_id, key))
                    new.append(TablePositionSensor(coordinator, row.team_id, key))
        if new:
            async_add_entities(new)

    _add_tables()
    entry.async_on_unload(coordinator.async_add_listener(_add_tables))


def _match_attrs(match: Match, team_id: int) -> dict[str, Any]:
    opponent = match.opponent(team_id)
    return {
        "competition": match.comp_name,
        "matchday": match.group,
        "opponent": opponent.name,
        "opponent_logo": opponent.icon,
        "home": match.is_home(team_id),
        "home_team": match.team1.name,
        "away_team": match.team2.name,
        "kickoff": match.kickoff.isoformat(),
        "venue": match.location,
    }


class NextMatchSensor(TeamEntity, SensorEntity):
    _attr_translation_key = "next_match"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_next_match"

    def _match(self) -> Match | None:
        return next_match(self.coordinator.team_matches(self.team_id), dt_util.utcnow())

    @property
    def native_value(self) -> datetime | None:
        match = self._match()
        return match.kickoff if match else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        match = self._match()
        return _match_attrs(match, self.team_id) if match else None


class LastMatchSensor(TeamEntity, SensorEntity):
    """Result of the last finished match, own goals first (e.g. "2:1")."""

    _attr_translation_key = "last_match"

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_last_match"

    def _match(self) -> Match | None:
        return last_match(self.coordinator.team_matches(self.team_id))

    @property
    def native_value(self) -> str | None:
        match = self._match()
        score = match.score_for(self.team_id, match.final) if match else None
        return f"{score[0]}:{score[1]}" if score else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        match = self._match()
        if not match or match.final is None:
            return None
        own, opp = match.score_for(self.team_id, match.final)
        return _match_attrs(match, self.team_id) | {
            "score_home": match.final[0],
            "score_away": match.final[1],
            "result": "win" if own > opp else "loss" if own < opp else "draw",
        }


class MatchStatusSensor(TeamEntity, SensorEntity):
    """`live` while a match of the team is running, otherwise `idle`."""

    _attr_translation_key = "match_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["idle", "live"]

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_match_status"

    def _match(self) -> Match | None:
        return live_match(self.coordinator.team_matches(self.team_id), dt_util.utcnow())

    @property
    def native_value(self) -> str:
        return "live" if self._match() else "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        match = self._match()
        if not match:
            return None
        score = match.score_for(self.team_id, match.live)
        return _match_attrs(match, self.team_id) | {
            "score": f"{score[0]}:{score[1]}" if score else None,
        }


class TablePositionSensor(TeamEntity, SensorEntity):
    _attr_translation_key = "table_position"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int, comp_key: str) -> None:
        super().__init__(coordinator, team_id)
        self.comp_key = comp_key
        self._attr_unique_id = f"{self._base_id}_table_{comp_key}"
        self._attr_translation_placeholders = {"competition": COMPETITIONS[comp_key]["name"]}

    def _row(self):
        rows = self.coordinator.data.tables.get(self.comp_key, []) if self.coordinator.data else []
        return next((r for r in rows if r.team_id == self.team_id), None)

    @property
    def available(self) -> bool:
        return super().available and self._row() is not None

    @property
    def native_value(self) -> int | None:
        row = self._row()
        return row.position if row else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        row = self._row()
        if not row:
            return None
        return {
            "competition": COMPETITIONS[self.comp_key]["name"],
            "points": row.points,
            "played": row.played,
            "won": row.won,
            "draw": row.draw,
            "lost": row.lost,
            "goals_for": row.goals_for,
            "goals_against": row.goals_against,
            "goal_difference": row.goal_difference,
        }
