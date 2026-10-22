"""HTTP view serving team logos that OpenLigaDB only provides as embedded data: URIs."""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import STATIC_BASE_URL
from .logos import decode_data_uri
from .model import EMBEDDED_LOGOS


class TeamLogoView(HomeAssistantView):
    """`/ligatracker_frontend/team-logo/<team id>`.

    Public like the other bundled static files: it is requested by <img> tags, which cannot send
    an authorization header, and only ever returns logos taken from OpenLigaDB match data.
    """

    url = STATIC_BASE_URL + "/team-logo/{team_id}"
    name = "ligatracker:team_logo"
    requires_auth = False

    async def get(self, request: web.Request, team_id: str) -> web.Response:
        uri = EMBEDDED_LOGOS.get(int(team_id)) if team_id.isdigit() else None
        logo = decode_data_uri(uri) if uri else None
        if logo is None:
            raise web.HTTPNotFound
        content, content_type = logo
        return web.Response(
            body=content,
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
        )
