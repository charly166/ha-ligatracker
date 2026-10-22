"""Bundled competition logos."""

from __future__ import annotations

from pathlib import Path

from custom_components.ligatracker.const import BUNDLED_LOGOS, COMPETITION_LOGOS, COMPETITIONS

_LOGOS = Path(__file__).parent.parent / "custom_components" / "ligatracker" / "logos"


def test_bundled_logo_files_exist_and_are_png() -> None:
    for key, name in BUNDLED_LOGOS.items():
        data = (_LOGOS / name).read_bytes()
        assert data[1:4] == b"PNG", key
        assert COMPETITION_LOGOS[key] == f"/ligatracker_frontend/logos/{name}"


def test_logos_are_square_so_the_image_entity_does_not_crop_them() -> None:
    import struct

    for key, name in BUNDLED_LOGOS.items():
        width, height = struct.unpack(">II", (_LOGOS / name).read_bytes()[16:24])
        assert width == height, f"{key}: {width}x{height}"


def test_every_competition_has_a_logo() -> None:
    assert set(COMPETITION_LOGOS) == set(COMPETITIONS)
    assert set(BUNDLED_LOGOS) == set(COMPETITIONS)
