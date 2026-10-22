"""Sensor platform: next match, last result, live status and table position."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .const import COMPETITIONS
from .coordinator import LigaTrackerCoordinator
from .entity import TeamEntity
from .model import Match, last_match, live_match, next_match
from .overview import build_overview


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
            OverviewSensor(coordinator, team_id),
            MatchFieldSensor(coordinator, team_id, "next", "opponent"),
            MatchFieldSensor(coordinator, team_id, "next", "competition"),
            MatchFieldSensor(coordinator, team_id, "last", "opponent"),
            MatchFieldSensor(coordinator, team_id, "last", "competition"),
            MatchFieldSensor(coordinator, team_id, "next", "home_away"),
            MatchFieldSensor(coordinator, team_id, "last", "home_away"),
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


class TeamLogoPictureMixin:
    """Shows the team's own logo as the entity picture."""

    coordinator: LigaTrackerCoordinator
    team_id: int

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.team_icon(self.team_id)


def _match_attrs(match: Match, team_id: int, team_logo: str | None = None) -> dict[str, Any]:
    opponent = match.opponent(team_id)
    return {
        "team_logo": team_logo,
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


class NextMatchSensor(TeamLogoPictureMixin, TeamEntity, SensorEntity):
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
        return _match_attrs(match, self.team_id, self.coordinator.team_icon(self.team_id)) if match else None


class LastMatchSensor(TeamLogoPictureMixin, TeamEntity, SensorEntity):
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
        return _match_attrs(match, self.team_id, self.coordinator.team_icon(self.team_id)) | {
            "score_home": match.final[0],
            "score_away": match.final[1],
            "result": "win" if own > opp else "loss" if own < opp else "draw",
        }


class MatchFieldSensor(TeamEntity, SensorEntity):
    """Opponent or competition of the next / last match as a stand-alone sensor."""

    def __init__(
        self, coordinator: LigaTrackerCoordinator, team_id: int, which: str, field: str
    ) -> None:
        super().__init__(coordinator, team_id)
        self._which = which
        self._field = field
        self._attr_translation_key = f"{which}_{field}"
        self._attr_unique_id = f"{self._base_id}_{which}_{field}"
        if field == "home_away":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["home", "away"]

    def _match(self) -> Match | None:
        matches = self.coordinator.team_matches(self.team_id)
        if self._which == "next":
            return next_match(matches, dt_util.utcnow())
        return last_match(matches)

    @property
    def native_value(self) -> str | None:
        match = self._match()
        if not match:
            return None
        if self._field == "competition":
            return match.comp_name
        if self._field == "home_away":
            return "home" if match.is_home(self.team_id) else "away"
        return match.opponent(self.team_id).name

    @property
    def entity_picture(self) -> str | None:
        match = self._match()
        if match and self._field == "opponent":
            return match.opponent(self.team_id).icon
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        match = self._match()
        if not match:
            return None
        if self._field == "competition":
            return {"matchday": match.group}
        if self._field == "home_away":
            return {"opponent": match.opponent(self.team_id).name, "competition": match.comp_name}
        return {"home": match.is_home(self.team_id), "competition": match.comp_name}


class OverviewSensor(TeamEntity, SensorEntity):
    """All competitions of a team in one structured attribute; data source of the team card."""

    _attr_translation_key = "overview"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _unrecorded_attributes = frozenset({"team", "competitions"})

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_overview"

    def _overview(self) -> dict[str, Any]:
        data = self.coordinator.data
        return build_overview(
            self.team_id,
            self.coordinator.teams[self.team_id],
            self.coordinator.team_icon(self.team_id),
            data.matches if data else {},
            data.tables if data else {},
            dt_util.utcnow(),
        )

    @property
    def native_value(self) -> int:
        """Number of competitions the team plays in."""
        return len(self._overview()["competitions"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._overview()


class MatchStatusSensor(TeamLogoPictureMixin, TeamEntity, SensorEntity):
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
        return _match_attrs(match, self.team_id, self.coordinator.team_icon(self.team_id)) | {
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
