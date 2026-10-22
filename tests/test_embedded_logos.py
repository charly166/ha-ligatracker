"""Logos that OpenLigaDB embeds as data: URIs are served through a short URL."""

from __future__ import annotations

import asyncio

import pytest
from aiohttp import web

from custom_components.ligatracker.logos import decode_data_uri
from custom_components.ligatracker.model import EMBEDDED_LOGOS, _team
from custom_components.ligatracker.views import TeamLogoView

# 1x1 transparent PNG
_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _raw(team_id: int, icon: str | None) -> dict:
    return {"teamId": team_id, "teamName": "Aston Villa", "shortName": "Villa", "teamIconUrl": icon}


def test_embedded_logo_gets_short_url_not_the_data_uri() -> None:
    team = _team(_raw(438, _PNG))
    assert team.icon == "/ligatracker_frontend/team-logo/438"
    assert EMBEDDED_LOGOS[438] == _PNG


def test_unusable_data_uris_are_dropped() -> None:
    assert _team(_raw(1, "data:text/html;base64,PHNjcmlwdD4=")).icon is None  # not an image
    assert _team(_raw(2, "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=")).icon is None  # svg: no
    assert _team(_raw(3, "data:image/png;base64," + "A" * 400_000)).icon is None  # too large
    assert _team(_raw(4, None)).icon is None


def test_http_urls_are_unchanged() -> None:
    assert _team(_raw(5, "https://i.imgur.com/x.png")).icon == "https://i.imgur.com/x.png"
    assert _team(_raw(6, "http://img.uefa.com/a.png")).icon == "https://img.uefa.com/a.png"


def test_decode_data_uri() -> None:
    content, content_type = decode_data_uri(_PNG)
    assert content[1:4] == b"PNG" and content_type == "image/png"
    assert decode_data_uri("data:image/png;base64,AAAA") is None  # not a real image


def test_view_serves_the_logo_and_404s_otherwise() -> None:
    _team(_raw(438, _PNG))
    view = TeamLogoView()

    async def run() -> None:
        response = await view.get(None, "438")
        assert response.status == 200 and response.content_type == "image/png"
        assert response.body[1:4] == b"PNG"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        for bad in ("999999", "abc", "../x"):
            with pytest.raises(web.HTTPNotFound):
                await view.get(None, bad)

    asyncio.run(run())
