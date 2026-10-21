"""Async client for the OpenLigaDB API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import API_BASE, COMPETITIONS
from .model import Match, TableRow, parse_match, parse_table

_LOGGER = logging.getLogger(__name__)


class OpenLigaDBError(Exception):
    """Raised when the API cannot be reached or returns garbage."""


class OpenLigaDBClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str) -> Any:
        try:
            async with asyncio.timeout(20):
                resp = await self._session.get(f"{API_BASE}/{path}")
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise OpenLigaDBError(f"{path}: {err}") from err

    async def get_matches(self, shortcut: str, season: int) -> list[dict[str, Any]]:
        data = await self._get(f"getmatchdata/{quote(shortcut, safe='')}/{season}")
        if not isinstance(data, list):
            raise OpenLigaDBError(f"unexpected match data for {shortcut}/{season}")
        return data

    async def get_table(self, shortcut: str, season: int) -> list[TableRow]:
        data = await self._get(f"getbltable/{quote(shortcut, safe='')}/{season}")
        return parse_table(data) if isinstance(data, list) else []


class CompetitionLoader:
    """Resolves the best OpenLigaDB shortcut per competition and season."""

    def __init__(self, client: OpenLigaDBClient) -> None:
        self._client = client
        self._shortcuts: dict[tuple[str, int], str] = {}

    async def matches(self, key: str, season: int) -> list[Match]:
        comp = COMPETITIONS[key]
        known = self._shortcuts.get((key, season))
        if known:
            return self._parse(key, await self._client.get_matches(known, season))

        best: tuple[str, list[dict[str, Any]]] | None = None
        last_error: OpenLigaDBError | None = None
        for shortcut in comp["shortcuts"]:
            try:
                raw = await self._client.get_matches(shortcut, season)
            except OpenLigaDBError as err:
                last_error = err
                continue
            if raw and (best is None or len(raw) > len(best[1])):
                best = (shortcut, raw)
        if best is None:
            if last_error:
                raise last_error
            return []  # competition does not exist for this season (yet)
        self._shortcuts[(key, season)] = best[0]
        _LOGGER.debug("%s %s: using shortcut %s", key, season, best[0])
        return self._parse(key, best[1])

    async def table(self, key: str, season: int) -> list[TableRow]:
        shortcut = self._shortcuts.get((key, season))
        if not shortcut or not COMPETITIONS[key]["table"]:
            return []
        return await self._client.get_table(shortcut, season)

    @staticmethod
    def _parse(key: str, raw: list[dict[str, Any]]) -> list[Match]:
        name = COMPETITIONS[key]["name"]
        matches = [m for r in raw if (m := parse_match(r, key, name))]
        matches.sort(key=lambda m: m.kickoff)
        return matches
