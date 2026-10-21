"""Config and options flow for Liga Tracker."""

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
from .const import COMPETITIONS, CONF_COMPETITIONS, CONF_TEAMS, DOMAIN
from .model import current_season


class _FlowMixin:
    """Two-step selection (competitions, then teams) shared by config and options flow."""

    _competitions: list[str]

    async def _async_teams_for(self, competitions: list[str]) -> dict[int, str]:
        client = OpenLigaDBClient(async_get_clientsession(self.hass))  # type: ignore[attr-defined]
        loader = CompetitionLoader(client)
        season = current_season(dt_util.now())
        teams: dict[int, str] = {}
        for key in competitions:
            for match in await loader.matches(key, season):
                for team in (match.team1, match.team2):
                    teams[team.id] = team.name
        return teams

    @staticmethod
    def _competition_schema(default: list[str]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_COMPETITIONS, default=default): SelectSelector(
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


class LigaTrackerConfigFlow(_FlowMixin, ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._competitions = []
        self._teams: dict[int, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: LigaTrackerConfigEntry) -> OptionsFlow:
        return LigaTrackerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            self._competitions = user_input[CONF_COMPETITIONS]
            if not self._competitions:
                errors["base"] = "no_competition"
            else:
                try:
                    self._teams = await self._async_teams_for(self._competitions)
                except OpenLigaDBError:
                    errors["base"] = "cannot_connect"
                else:
                    if not self._teams:
                        errors["base"] = "no_teams"
                    else:
                        return await self.async_step_teams()
        return self.async_show_form(
            step_id="user",
            data_schema=self._competition_schema(self._competitions or ["bl1"]),
            errors=errors,
        )

    async def async_step_teams(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_TEAMS]:
                errors["base"] = "no_team"
            else:
                return self.async_create_entry(
                    title="Liga Tracker",
                    data={
                        CONF_COMPETITIONS: self._competitions,
                        CONF_TEAMS: {t: self._teams[int(t)] for t in user_input[CONF_TEAMS]},
                    },
                )
        return self.async_show_form(
            step_id="teams", data_schema=self._team_schema(self._teams, []), errors=errors
        )


class LigaTrackerOptionsFlow(_FlowMixin, OptionsFlow):
    def __init__(self) -> None:
        self._competitions = []
        self._teams: dict[int, str] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._competitions = user_input[CONF_COMPETITIONS]
            if not self._competitions:
                errors["base"] = "no_competition"
            else:
                try:
                    self._teams = await self._async_teams_for(self._competitions)
                except OpenLigaDBError:
                    errors["base"] = "cannot_connect"
                else:
                    # keep teams that were selected before, even if currently not listed
                    for tid, name in self.config_entry.data[CONF_TEAMS].items():
                        self._teams.setdefault(int(tid), name)
                    return await self.async_step_teams()
        return self.async_show_form(
            step_id="init",
            data_schema=self._competition_schema(
                self._competitions or list(self.config_entry.data[CONF_COMPETITIONS])
            ),
            errors=errors,
        )

    async def async_step_teams(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_TEAMS]:
                errors["base"] = "no_team"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_COMPETITIONS: self._competitions,
                        CONF_TEAMS: {t: self._teams[int(t)] for t in user_input[CONF_TEAMS]},
                    },
                )
                return self.async_create_entry(data={})
        current = [t for t in self.config_entry.data[CONF_TEAMS] if int(t) in self._teams]
        return self.async_show_form(
            step_id="teams", data_schema=self._team_schema(self._teams, current), errors=errors
        )
