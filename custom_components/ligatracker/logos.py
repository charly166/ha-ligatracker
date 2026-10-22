"""Disk-backed cache for club logos.

Logos are fetched once and kept in the config directory. A failed download is not
retried for a while, so a rate-limited host (e.g. HTTP 429) is not hammered by every
dashboard refresh or integration reload.
"""

from __future__ import annotations

import asyncio
from hashlib import sha1
import logging
from pathlib import Path
import time

import aiohttp

from homeassistant.components.image import infer_image_type
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

RETRY_AFTER = 30 * 60  # seconds before a failed download is tried again
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "HA-Liga-Tracker (Home Assistant custom integration)"


class LogoCache:
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._dir = Path(hass.config.path(".storage", "ligatracker_logos"))
        self._failed: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _file(self, url: str) -> Path:
        return self._dir / sha1(url.encode()).hexdigest()  # noqa: S324 - not security relevant

    def _read(self, url: str) -> bytes | None:
        try:
            return self._file(url).read_bytes()
        except OSError:
            return None

    def _write(self, url: str, content: bytes) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._file(url).write_bytes(content)
        except OSError as err:
            _LOGGER.debug("Could not cache logo %s: %s", url, err)

    async def get(self, url: str) -> tuple[bytes, str] | None:
        """Return (content, content type) for a logo URL, or None."""
        async with self._locks.setdefault(url, asyncio.Lock()):
            content = await self._hass.async_add_executor_job(self._read, url)
            if content is None:
                content = await self._download(url)
                if content is None:
                    return None
                await self._hass.async_add_executor_job(self._write, url, content)
        content_type = infer_image_type(content)
        return (content, content_type) if content_type else None

    async def _download(self, url: str) -> bytes | None:
        failed_at = self._failed.get(url)
        if failed_at is not None and time.monotonic() - failed_at < RETRY_AFTER:
            return None
        try:
            async with asyncio.timeout(15):
                resp = await async_get_clientsession(self._hass).get(
                    url, headers={"User-Agent": USER_AGENT}
                )
                resp.raise_for_status()
                if (resp.content_length or 0) > MAX_BYTES:
                    raise aiohttp.ClientError("logo too large")
                content = await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            self._failed[url] = time.monotonic()
            _LOGGER.warning("Logo %s not available (retry in %d min): %s", url, RETRY_AFTER // 60, err)
            return None
        if len(content) > MAX_BYTES or infer_image_type(content) is None:
            self._failed[url] = time.monotonic()
            _LOGGER.warning("Logo %s is not a usable image (retry in %d min)", url, RETRY_AFTER // 60)
            return None
        self._failed.pop(url, None)
        return content


def get_logo_cache(hass: HomeAssistant) -> LogoCache:
    """One cache per Home Assistant instance, so back-off survives integration reloads."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if "logos" not in domain_data:
        domain_data["logos"] = LogoCache(hass)
    return domain_data["logos"]
