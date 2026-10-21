"""Pure data model and parsing for OpenLigaDB responses (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .const import MATCH_WINDOW, PRE_KICKOFF


def current_season(now: datetime) -> int:
    """Season is identified by its start year (2026 = 2026/27)."""
    return now.year if now.month >= 7 else now.year - 1


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    short: str
    icon: str | None


@dataclass(frozen=True)
class Match:
    id: int
    comp_key: str
    comp_name: str
    kickoff: datetime
    group: str
    team1: Team
    team2: Team
    finished: bool
    final: tuple[int, int] | None
    live: tuple[int, int] | None
    location: str | None

    def involves(self, team_id: int) -> bool:
        return team_id in (self.team1.id, self.team2.id)

    def is_home(self, team_id: int) -> bool:
        return self.team1.id == team_id

    def opponent(self, team_id: int) -> Team:
        return self.team2 if self.is_home(team_id) else self.team1

    def score_for(self, team_id: int, score: tuple[int, int] | None) -> tuple[int, int] | None:
        """Return (own, opponent) goals from the team's point of view."""
        if score is None:
            return None
        return score if self.is_home(team_id) else (score[1], score[0])

    def is_live(self, now: datetime) -> bool:
        return not self.finished and self.kickoff <= now < self.kickoff + MATCH_WINDOW

    def is_active(self, now: datetime) -> bool:
        """Live, or about to start - used to speed up polling."""
        return not self.finished and self.kickoff - PRE_KICKOFF <= now < self.kickoff + MATCH_WINDOW


@dataclass(frozen=True)
class TableRow:
    team_id: int
    name: str
    position: int
    points: int
    played: int
    won: int
    draw: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int


def _team(raw: dict[str, Any]) -> Team:
    icon = raw.get("teamIconUrl")
    # Some entries embed huge data: URIs - never put those into state attributes.
    if not (isinstance(icon, str) and icon.startswith(("http://", "https://"))):
        icon = None
    name = raw.get("teamName") or "?"
    return Team(int(raw["teamId"]), name.strip(), (raw.get("shortName") or name).strip(), icon)


def parse_match(raw: dict[str, Any], comp_key: str, comp_name: str) -> Match | None:
    """Parse one match, or None if it lacks the data we need."""
    try:
        kickoff = datetime.fromisoformat(raw["matchDateTimeUTC"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        team1, team2 = _team(raw["team1"]), _team(raw["team2"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return None

    results = raw.get("matchResults") or []
    finished = bool(raw.get("matchIsFinished"))
    final = next((r for r in results if r.get("resultTypeID") == 2), None)
    latest = max(results, key=lambda r: r.get("resultOrderID") or 0) if results else None

    def score(res: dict[str, Any] | None) -> tuple[int, int] | None:
        if not res or res.get("pointsTeam1") is None or res.get("pointsTeam2") is None:
            return None
        return int(res["pointsTeam1"]), int(res["pointsTeam2"])

    loc = raw.get("location") or {}
    return Match(
        id=int(raw["matchID"]),
        comp_key=comp_key,
        comp_name=comp_name,
        kickoff=kickoff,
        group=(raw.get("group") or {}).get("groupName") or "",
        team1=team1,
        team2=team2,
        finished=finished,
        final=score(final) if finished else None,
        live=None if finished else score(latest),
        location=loc.get("locationStadium") or loc.get("locationCity") or None,
    )


def parse_table(raw: list[dict[str, Any]]) -> list[TableRow]:
    rows = []
    for pos, r in enumerate(raw, start=1):
        try:
            rows.append(
                TableRow(
                    team_id=int(r["teamInfoId"]),
                    name=(r.get("teamName") or "?").strip(),
                    position=pos,
                    points=int(r["points"]),
                    played=int(r["matches"]),
                    won=int(r["won"]),
                    draw=int(r["draw"]),
                    lost=int(r["lost"]),
                    goals_for=int(r["goals"]),
                    goals_against=int(r["opponentGoals"]),
                    goal_difference=int(r["goalDiff"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def next_match(matches: list[Match], now: datetime) -> Match | None:
    return next((m for m in matches if not m.finished and m.kickoff > now), None)


def last_match(matches: list[Match]) -> Match | None:
    done = [m for m in matches if m.finished and m.final is not None]
    return done[-1] if done else None


def live_match(matches: list[Match], now: datetime) -> Match | None:
    return next((m for m in matches if m.is_live(now)), None)
