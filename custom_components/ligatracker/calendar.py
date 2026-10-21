"""Calendar platform: one calendar per team and per selected league."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .const import EVENT_LENGTH
from .entity import LeagueEntity, TeamEntity
from .model import Match


def _event(match: Match) -> CalendarEvent:
    if match.finished and match.final is not None:
        summary = f"{match.team1.name} {match.final[0]}:{match.final[1]} {match.team2.name}"
    else:
        summary = f"{match.team1.name} – {match.team2.name}"
    description = " · ".join(p for p in (match.comp_name, match.group) if p)
    return CalendarEvent(
        start=match.kickoff,
        end=match.kickoff + EVENT_LENGTH,
        summary=summary,
        description=description,
        location=match.location,
        uid=f"ligatracker-{match.id}",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LigaTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [TeamCalendar(coordinator, t) for t in coordinator.teams]
        + [LeagueCalendar(coordinator, k) for k in coordinator.leagues]
    )


def _running_or_next(matches: list[Match]) -> CalendarEvent | None:
    now = dt_util.utcnow()
    for match in matches:
        if not match.finished and match.kickoff + EVENT_LENGTH > now:
            return _event(match)
    return None


def _in_range(matches: list[Match], start: datetime, end: datetime) -> list[CalendarEvent]:
    return [_event(m) for m in matches if m.kickoff < end and m.kickoff + EVENT_LENGTH > start]


class TeamCalendar(TeamEntity, CalendarEntity):
    """All matches of one team in the selected competitions."""

    _attr_name = None  # use the team (device) name

    def __init__(self, coordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """The running match, otherwise the next one."""
        return _running_or_next(self.coordinator.team_matches(self.team_id))

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return _in_range(self.coordinator.team_matches(self.team_id), start_date, end_date)


class LeagueCalendar(LeagueEntity, CalendarEntity):
    """All matches of one league/competition."""

    _attr_name = None  # use the competition (device) name

    def __init__(self, coordinator, comp_key: str) -> None:
        super().__init__(coordinator, comp_key)
        self._attr_unique_id = f"{self._base_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        return _running_or_next(self.coordinator.league_matches(self.comp_key))

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return _in_range(self.coordinator.league_matches(self.comp_key), start_date, end_date)
