"""Data update coordinator for HA Liga Tracker."""

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
    COMPETITIONS,
    CONF_LEAGUES,
    CONF_TEAMS,
    DISCOVERY_INTERVAL,
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
    """Fetches the competitions the selected teams play in plus the selected leagues."""

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
        # team id -> display name
        self.teams: dict[int, str] = {int(k): v for k, v in entry.data[CONF_TEAMS].items()}
        self.leagues: list[str] = [k for k in entry.data.get(CONF_LEAGUES, []) if k in COMPETITIONS]
        self._loader = CompetitionLoader(client)
        self._relevant: set[str] | None = None
        self._discovered: datetime | None = None
        self._discovered_season: int | None = None
        self._last_full: datetime | None = None

    def team_matches(self, team_id: int) -> list[Match]:
        """All known matches of a team across all competitions it plays in."""
        out = [
            m
            for ms in (self.data.matches if self.data else {}).values()
            for m in ms
            if m.involves(team_id)
        ]
        out.sort(key=lambda m: m.kickoff)
        return out

    def team_icon(self, team_id: int) -> str | None:
        """Logo URL of a team; the icon differs between competitions, prefer https."""
        icons = [
            (m.team1 if m.team1.id == team_id else m.team2).icon
            for m in self.team_matches(team_id)
        ]
        icons = [i for i in icons if i]
        return next((i for i in icons if i.startswith("https://")), icons[0] if icons else None)

    def league_matches(self, key: str) -> list[Match]:
        return self.data.matches.get(key, []) if self.data else []

    def _is_tracked_active(self, m: Match, now: datetime) -> bool:
        return m.is_active(now) and any(m.involves(t) for t in self.teams)

    def _active_competitions(self, data: LigaData | None, now: datetime) -> set[str]:
        if not data:
            return set()
        return {k for k, ms in data.matches.items() for m in ms if self._is_tracked_active(m, now)}

    async def _async_update_data(self) -> LigaData:
        now = dt_util.utcnow()
        season = current_season(dt_util.now())
        discover = (
            self._relevant is None
            or self._discovered_season != season
            or self._discovered is None
            or now - self._discovered >= DISCOVERY_INTERVAL
        )
        active = self._active_competitions(self.data, now)
        full = discover or not active or self._last_full is None or now - self._last_full >= FULL_REFRESH_INTERVAL

        if discover:
            keys = list(COMPETITIONS)
        elif full:
            keys = sorted(self._relevant or [])
        else:
            keys = sorted(active)

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

        if discover and not errors:
            self._relevant = {
                key
                for key, ms in data.matches.items()
                if key in self.leagues or any(m.involves(t) for m in ms for t in self.teams)
            }
            self._discovered, self._discovered_season = now, season
            # forget competitions that neither a team nor a league needs
            data.matches = {k: v for k, v in data.matches.items() if k in self._relevant}
            data.tables = {k: v for k, v in data.tables.items() if k in self._relevant}
        elif discover:
            # incomplete scan: keep whatever we got and retry next time
            self._relevant = self._relevant or {k for k, v in data.matches.items() if v}

        if errors and not data.matches:
            raise UpdateFailed("; ".join(errors))
        if full and not errors:
            self._last_full = now

        live = bool(self._active_competitions(data, now))
        self.update_interval = LIVE_INTERVAL if live else IDLE_INTERVAL
        return data
