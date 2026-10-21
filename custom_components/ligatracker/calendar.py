"""Calendar platform: one calendar per team with fixtures and results."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .const import EVENT_LENGTH
from .entity import TeamEntity
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
    async_add_entities(TeamCalendar(coordinator, team_id) for team_id in coordinator.teams)


class TeamCalendar(TeamEntity, CalendarEntity):
    """All matches of one team in the selected competitions."""

    _attr_name = None  # use the team (device) name

    def __init__(self, coordinator, team_id: int) -> None:
        super().__init__(coordinator, team_id)
        self._attr_unique_id = f"{self._base_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """The running match, otherwise the next one."""
        now = dt_util.utcnow()
        for match in self.coordinator.team_matches(self.team_id):
            if not match.finished and match.kickoff + EVENT_LENGTH > now:
                return _event(match)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _event(m)
            for m in self.coordinator.team_matches(self.team_id)
            if m.kickoff < end_date and m.kickoff + EVENT_LENGTH > start_date
        ]
