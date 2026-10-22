"""HA Liga Tracker: football fixtures and results from OpenLigaDB."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .api import OpenLigaDBClient
from .const import COMPETITIONS, CONF_LEAGUES, CONF_TEAMS, DOMAIN
from .coordinator import LigaTrackerCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.IMAGE, Platform.SENSOR]

type LigaTrackerConfigEntry = ConfigEntry[LigaTrackerCoordinator]

_CARD_URL = "/ligatracker_frontend/ligatracker-team-card.js"
_DATA_CARD_REGISTERED = f"{DOMAIN}_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled team card and load it in the frontend (once per run)."""
    if hass.data.get(_DATA_CARD_REGISTERED):
        return
    hass.data[_DATA_CARD_REGISTERED] = True
    path = Path(__file__).parent / "frontend" / "ligatracker-team-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_URL, str(path), cache_headers=False)]
    )
    version = (await async_get_integration(hass, DOMAIN)).version
    add_extra_js_url(hass, f"{_CARD_URL}?v={version}")


async def async_setup_entry(hass: HomeAssistant, entry: LigaTrackerConfigEntry) -> bool:
    await _async_register_card(hass)
    client = OpenLigaDBClient(async_get_clientsession(hass))
    coordinator = LigaTrackerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _async_remove_stale_devices(hass, entry, coordinator)

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


def _async_remove_stale_devices(
    hass: HomeAssistant, entry: LigaTrackerConfigEntry, coordinator: LigaTrackerCoordinator
) -> None:
    """Drop devices (and their entities) of teams/leagues that are no longer selected."""
    wanted = {f"{entry.entry_id}_{team_id}" for team_id in coordinator.teams} | {
        f"{entry.entry_id}_league_{key}" for key in coordinator.leagues if key in COMPETITIONS
    }
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        ours = {ident for domain, ident in device.identifiers if domain == DOMAIN}
        if ours and not ours & wanted:
            registry.async_remove_device(device.id)
