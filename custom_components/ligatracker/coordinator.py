"""Data update coordinator for Liga Tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CompetitionLoader, OpenLigaDBClient, OpenLigaDBError
from .const import (
    CONF_COMPETITIONS,
    CONF_TEAMS,
    DOMAIN,
    FULL_REFRESH_INTERVAL,
    IDLE_INTERVAL,
    LIVE_INTERVAL,
)
from .model import Match, TableRow, current_season

_LOGGER = logging.getLogger(__name__)


@dataclass
class LigaData:
    matches: dict[str, list[Match]] = field(default_factory=dict)
    tables: dict[str, list[TableRow]] = field(default_factory=dict)


class LigaTrackerCoordinator(DataUpdateCoordinator[LigaData]):
    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: OpenLigaDBClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=IDLE_INTERVAL,
        )
        self.competitions: list[str] = list(entry.data[CONF_COMPETITIONS])
        # team id -> display name
        self.teams: dict[int, str] = {int(k): v for k, v in entry.data[CONF_TEAMS].items()}
        self._loader = CompetitionLoader(client)
        self._last_full: datetime | None = None

    def team_matches(self, team_id: int) -> list[Match]:
        """All known matches of a team across the selected competitions."""
        out = [m for ms in (self.data.matches if self.data else {}).values() for m in ms if m.involves(team_id)]
        out.sort(key=lambda m: m.kickoff)
        return out

    def _active_competitions(self, now: datetime) -> set[str]:
        if not self.data:
            return set()
        return {
            key
            for key, ms in self.data.matches.items()
            for m in ms
            if m.is_active(now) and any(m.involves(t) for t in self.teams)
        }

    async def _async_update_data(self) -> LigaData:
        now = dt_util.utcnow()
        season = current_season(dt_util.now())
        active = self._active_competitions(now)
        full = (
            self._last_full is None
            or not active
            or now - self._last_full >= FULL_REFRESH_INTERVAL
        )
        keys = self.competitions if full else [k for k in self.competitions if k in active]

        data = LigaData(
            matches=dict(self.data.matches) if self.data else {},
            tables=dict(self.data.tables) if self.data else {},
        )
        errors: list[str] = []
        for key in keys:
            try:
                data.matches[key] = await self._loader.matches(key, season)
                if full:
                    data.tables[key] = await self._loader.table(key, season)
            except OpenLigaDBError as err:
                errors.append(str(err))
                _LOGGER.debug("Update of %s failed: %s", key, err)

        if errors and not data.matches:
            raise UpdateFailed("; ".join(errors))
        if full and not errors:
            self._last_full = now

        self.update_interval = LIVE_INTERVAL if self._active_competitions_in(data, now) else IDLE_INTERVAL
        return data

    def _active_competitions_in(self, data: LigaData, now: datetime) -> bool:
        return any(
            m.is_active(now) and any(m.involves(t) for t in self.teams)
            for ms in data.matches.values()
            for m in ms
        )
