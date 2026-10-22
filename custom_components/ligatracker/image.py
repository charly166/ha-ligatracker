"""Image platform: club logos of the teams and logos of the selected leagues."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.image import ImageEntity, infer_image_type
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LigaTrackerConfigEntry
from .const import BUNDLED_LOGOS
from .coordinator import LigaTrackerCoordinator
from .entity import LeagueEntity, TeamEntity
from .logos import get_logo_cache


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LigaTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [TeamLogo(coordinator, team_id) for team_id in coordinator.teams]
        + [LeagueLogo(coordinator, key) for key in coordinator.leagues if key in BUNDLED_LOGOS]
    )


class _CachedLogo(ImageEntity):
    """Serves the logo from the disk cache; never hits the remote host on every request."""

    async def async_image(self) -> bytes | None:
        if not (url := self._attr_image_url):
            return None
        if not (logo := await get_logo_cache(self.hass).get(url)):
            return None
        content, self._attr_content_type = logo
        return content


class TeamLogo(_CachedLogo, TeamEntity):
    """Club logo, usable in picture cards and as a source for dashboards."""

    _attr_translation_key = "logo"

    def __init__(self, coordinator: LigaTrackerCoordinator, team_id: int) -> None:
        TeamEntity.__init__(self, coordinator, team_id)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_unique_id = f"{self._base_id}_logo"
        self._attr_image_url = coordinator.team_icon(team_id)
        self._attr_image_last_updated = dt_util.utcnow()

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


class LeagueLogo(LeagueEntity, ImageEntity):
    """Logo of a selected league (the league card uses it as header image)."""

    _attr_translation_key = "league_logo"

    def __init__(self, coordinator: LigaTrackerCoordinator, comp_key: str) -> None:
        LeagueEntity.__init__(self, coordinator, comp_key)
        ImageEntity.__init__(self, coordinator.hass)
        self._attr_unique_id = f"{self._base_id}_logo"
        self._path = Path(__file__).parent / "logos" / BUNDLED_LOGOS[comp_key]
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        """The logo ships with the integration; no download needed."""
        content = await self.hass.async_add_executor_job(self._path.read_bytes)
        self._attr_content_type = infer_image_type(content) or "image/png"
        return content
