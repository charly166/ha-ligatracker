"""Pure tests for matchday selection (no Home Assistant fixtures needed)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.ligatracker.model import Match, Team, select_matchdays

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
_A, _B = Team(1, "A", "A", None), Team(2, "B", "B", None)


def _m(mid: int, order: int, hours: float, finished: bool) -> Match:
    return Match(
        id=mid,
        comp_key="bl1",
        comp_name="Bundesliga",
        kickoff=NOW + timedelta(hours=hours),
        group=f"{order}. Spieltag",
        group_order=order,
        team1=_A,
        team2=_B,
        finished=finished,
        final=(1, 0) if finished else None,
        live=None,
        location=None,
    )


def _ids(ms):
    return None if ms is None else [m.id for m in ms]


def test_between_matchdays() -> None:
    ms = [_m(1, 6, -100, True), _m(2, 6, -99, True), _m(3, 7, 24, False), _m(4, 7, 48, False)]
    last, nxt = select_matchdays(ms, NOW)
    assert _ids(last) == [1, 2] and _ids(nxt) == [3, 4]


def test_partly_played_matchday_is_next_and_previous_is_last() -> None:
    ms = [_m(1, 6, -200, True), _m(2, 7, -20, True), _m(3, 7, 24, False)]
    last, nxt = select_matchdays(ms, NOW)
    assert _ids(last) == [1] and _ids(nxt) == [2, 3]


def test_old_postponed_match_does_not_freeze_the_view() -> None:
    # matchday 5 still has an unfinished match from 40 days ago; the view must move on
    ms = [_m(1, 5, -24 * 40, False), _m(2, 6, -100, True), _m(3, 7, 24, False)]
    last, nxt = select_matchdays(ms, NOW)
    assert _ids(nxt) == [3]
    assert _ids(last) == [2]


def test_season_over_and_not_started() -> None:
    done = [_m(1, 33, -300, True), _m(2, 34, -200, True)]
    last, nxt = select_matchdays(done, NOW)
    assert _ids(last) == [2] and nxt is None
    fresh = [_m(1, 1, 100, False), _m(2, 1, 101, False)]
    last, nxt = select_matchdays(fresh, NOW)
    assert last is None and _ids(nxt) == [1, 2]
