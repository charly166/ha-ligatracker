"""Structured per-competition overview of a team (feeds the team card). No HA imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import COMPETITIONS
from .model import Match, TableRow, last_match, live_match, next_match

# Domestic leagues come first ("Liga"), everything else is listed under "other competitions".
LEAGUE_KEYS = ("bl1", "bl2", "bl3")


def _match_dict(match: Match, team_id: int) -> dict[str, Any]:
    score = match.final if match.finished else match.live
    result = None
    if match.finished and match.final is not None:
        own, opp = match.score_for(team_id, match.final) or (0, 0)
        result = "win" if own > opp else "loss" if own < opp else "draw"
    return {
        "home": match.team1.name,
        "home_short": match.team1.short,
        "home_logo": match.team1.icon,
        "away": match.team2.name,
        "away_short": match.team2.short,
        "away_logo": match.team2.icon,
        "score": list(score) if score is not None else None,
        "kickoff": match.kickoff.isoformat(),
        "matchday": match.group,
        "venue": match.location,
        "team_is_home": match.is_home(team_id),
        "result": result,
    }


def _table_dict(rows: list[TableRow], team_id: int) -> dict[str, Any] | None:
    row = next((r for r in rows if r.team_id == team_id), None)
    if row is None:
        return None
    return {
        "position": row.position,
        "points": row.points,
        "played": row.played,
        "goal_difference": row.goal_difference,
    }


def build_overview(
    team_id: int,
    team_name: str,
    team_logo: str | None,
    matches_by_comp: dict[str, list[Match]],
    tables: dict[str, list[TableRow]],
    now: datetime,
) -> dict[str, Any]:
    """Competitions the team plays in, leagues first, each with table/last/next/live."""
    competitions: list[dict[str, Any]] = []
    for key, comp in COMPETITIONS.items():
        mine = sorted((m for m in matches_by_comp.get(key, []) if m.involves(team_id)), key=lambda m: m.kickoff)
        if not mine:
            continue
        last, nxt, live = last_match(mine), next_match(mine, now), live_match(mine, now)
        competitions.append(
            {
                "key": key,
                "name": comp["name"],
                "league": key in LEAGUE_KEYS,
                "table": _table_dict(tables.get(key, []), team_id),
                "last": _match_dict(last, team_id) if last else None,
                "next": _match_dict(nxt, team_id) if nxt else None,
                "live": _match_dict(live, team_id) if live else None,
            }
        )
    competitions.sort(key=lambda c: not c["league"])  # stable: leagues first
    return {
        "team": {"id": team_id, "name": team_name, "logo": team_logo},
        "competitions": competitions,
    }
