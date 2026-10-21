"""Base entities for HA Liga Tracker."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, COMPETITIONS, DOMAIN
from .coordinator import LigaTrackerCoordinator


class TeamEntity(CoordinatorEntity[LigaTrackerCoordinator]):
    """Entity belonging to the device of one team."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        super().__init__(coordinator)
        self.team_id = team_id
        entry_id = coordinator.config_entry.entry_id
        self._base_id = f"{entry_id}_{team_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._base_id)},
            name=coordinator.teams[team_id],
            manufacturer="OpenLigaDB",
        )


class LeagueEntity(CoordinatorEntity[LigaTrackerCoordinator]):
    """Entity belonging to the device of one league/competition."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: LigaTrackerCoordinator, comp_key: str) -> None:
        super().__init__(coordinator)
        self.comp_key = comp_key
        self._base_id = f"{coordinator.config_entry.entry_id}_league_{comp_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._base_id)},
            name=COMPETITIONS[comp_key]["name"],
            manufacturer="OpenLigaDB",
        )
