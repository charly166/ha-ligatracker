"""Config and options flow for HA Liga Tracker."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .api import CompetitionLoader, OpenLigaDBClient, OpenLigaDBError
from .const import COMPETITIONS, CONF_LEAGUES, CONF_TEAMS, DOMAIN, NAME
from .model import current_season


class _FlowMixin:
    """Step 1: teams, step 2: optional leagues - shared by config and options flow."""

    _teams: dict[int, str]
    _selected: list[str]

    async def _async_all_teams(self) -> dict[int, str]:
        """All teams that appear in any curated competition this season."""
        client = OpenLigaDBClient(async_get_clientsession(self.hass))  # type: ignore[attr-defined]
        loader = CompetitionLoader(client)
        season = current_season(dt_util.now())
        teams: dict[int, str] = {}
        errors = 0
        for key in COMPETITIONS:
            try:
                matches = await loader.matches(key, season)
            except OpenLigaDBError:
                errors += 1
                continue
            for match in matches:
                for team in (match.team1, match.team2):
                    teams[team.id] = team.name
        if errors == len(COMPETITIONS):
            raise OpenLigaDBError("no competition could be loaded")
        return teams

    @staticmethod
    def _team_schema(teams: dict[int, str], default: list[str]) -> vol.Schema:
        options = [
            SelectOptionDict(value=str(tid), label=name)
            for tid, name in sorted(teams.items(), key=lambda kv: kv[1].casefold())
        ]
        return vol.Schema(
            {
                vol.Required(CONF_TEAMS, default=default): SelectSelector(
                    SelectSelectorConfig(
                        options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN
                    )
                )
            }
        )

    @staticmethod
    def _league_schema(default: list[str]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(CONF_LEAGUES, default=default): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=k, label=v["name"])
                            for k, v in COMPETITIONS.items()
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )

    def _entry_data(self, leagues: list[str]) -> dict[str, Any]:
        return {
            CONF_TEAMS: {t: self._teams[int(t)] for t in self._selected},
            CONF_LEAGUES: leagues,
        }


class LigaTrackerConfigFlow(_FlowMixin, ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._teams = {}
        self._selected = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: LigaTrackerConfigEntry) -> OptionsFlow:
        return LigaTrackerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if not self._teams:
            try:
                self._teams = await self._async_all_teams()
            except OpenLigaDBError:
                return self.async_abort(reason="cannot_connect")
        if user_input is not None:
            self._selected = user_input[CONF_TEAMS]
            if self._selected:
                return await self.async_step_leagues()
            errors["base"] = "no_team"
        return self.async_show_form(
            step_id="user",
            data_schema=self._team_schema(self._teams, self._selected),
            errors=errors,
        )

    async def async_step_leagues(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=NAME, data=self._entry_data(user_input.get(CONF_LEAGUES, []))
            )
        return self.async_show_form(step_id="leagues", data_schema=self._league_schema([]))


class LigaTrackerOptionsFlow(_FlowMixin, OptionsFlow):
    def __init__(self) -> None:
        self._teams = {}
        self._selected = []

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if not self._teams:
            try:
                self._teams = await self._async_all_teams()
            except OpenLigaDBError:
                return self.async_abort(reason="cannot_connect")
            # keep teams that were selected before, even if currently not listed
            for tid, name in self.config_entry.data[CONF_TEAMS].items():
                self._teams.setdefault(int(tid), name)
        if user_input is not None:
            self._selected = user_input[CONF_TEAMS]
            if self._selected:
                return await self.async_step_leagues()
            errors["base"] = "no_team"
        return self.async_show_form(
            step_id="init",
            data_schema=self._team_schema(
                self._teams, self._selected or list(self.config_entry.data[CONF_TEAMS])
            ),
            errors=errors,
        )

    async def async_step_leagues(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self._entry_data(user_input.get(CONF_LEAGUES, []))
            )
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="leagues",
            data_schema=self._league_schema(list(self.config_entry.data.get(CONF_LEAGUES, []))),
        )
