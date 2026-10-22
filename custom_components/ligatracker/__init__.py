"""HA Liga Tracker: football fixtures and results from OpenLigaDB."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenLigaDBClient
from .const import CONF_LEAGUES, CONF_TEAMS
from .coordinator import LigaTrackerCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.IMAGE, Platform.SENSOR]

type LigaTrackerConfigEntry = ConfigEntry[LigaTrackerCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LigaTrackerConfigEntry) -> bool:
    client = OpenLigaDBClient(async_get_clientsession(hass))
    coordinator = LigaTrackerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LigaTrackerConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: LigaTrackerConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: LigaTrackerConfigEntry) -> bool:
    """v1 selected competitions + teams; v2 selects teams + optional whole-league calendars."""
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry,
            data={CONF_TEAMS: entry.data[CONF_TEAMS], CONF_LEAGUES: []},
            title="HA Liga Tracker",
            version=2,
        )
    return True
