"""Image platform: the team's club logo."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .coordinator import LigaTrackerCoordinator
from .entity import TeamEntity
from .logos import get_logo_cache


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LigaTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(TeamLogo(coordinator, team_id) for team_id in coordinator.teams)


class TeamLogo(TeamEntity, ImageEntity):
    """Club logo, usable in picture cards and as a source for dashboards."""

    _attr_translation_key = "logo"

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        TeamEntity.__init__(self, coordinator, team_id)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_unique_id = f"{self._base_id}_logo"
        self._attr_image_url = coordinator.team_icon(team_id)
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        """Serve the logo from the disk cache; never hit the remote host on every request."""
        if not (url := self._attr_image_url):
            return None
        if not (logo := await get_logo_cache(self.hass).get(url)):
            return None
        content, self._attr_content_type = logo
        return content

    @callback
    def _handle_coordinator_update(self) -> None:
        url = self.coordinator.team_icon(self.team_id)
        if url != self._attr_image_url:
            self._attr_image_url = url
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return super().available and self._attr_image_url is not None
