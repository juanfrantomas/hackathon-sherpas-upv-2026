"""The decision laboratory.

The plan already says which steps raise the score, on its own: the
``top_moves`` carry their individual score and the ``combined_moves`` say what
a set of them achieves together.  The simulator does not invent any of it: it
reads those figures and shows what happens when the household switches a
decision on.

Everything here is pure arithmetic over the plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


def slug_of(value: str) -> str:
    """A stable identifier for a step of the plan."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return cleaned or "step"


@dataclass
class PowerUp:
    """One decision the household can switch on."""

    id: str
    title: str
    action: str
    score_before: int
    score_after: int
    active: bool = False
    icon: str = ""
    effort: str = ""
    lock_label: str = ""
    individual_impact: str = ""
    mentor_question: str = ""

    @property
    def score_impact(self) -> int:
        return max(0, self.score_after - self.score_before)


@dataclass
class Simulation:
    """What the plan says about the decisions the household switched on."""

    score_base: int = 0
    score_simulated: int = 0
    score_delta: int = 0
    synergy_detected: bool = False
    synergy_score: int = 0
    power_ups: list[PowerUp] = field(default_factory=list)
    active_ids: list[str] = field(default_factory=list)
    active_titles: list[str] = field(default_factory=list)

    @property
    def next_steps(self) -> list[str]:
        """The action of every decision that is switched on."""
        return [power_up.action for power_up in self.power_ups if power_up.active]


def _moves_of(score_block: dict[str, Any]) -> list[dict[str, Any]]:
    moves = score_block.get("top_moves") or []
    return [move for move in moves if isinstance(move, dict) and move.get("title")]


def _combos_of(score_block: dict[str, Any]) -> list[dict[str, Any]]:
    combos = score_block.get("combined_moves") or []
    return [combo for combo in combos if isinstance(combo, dict) and combo.get("moves")]


def simulate(score_block: dict[str, Any], active_ids: list[str] | None = None) -> Simulation:
    """The score the plan reaches with the given decisions switched on.

    The combined score of a set of steps is taken from the plan when it has
    one; otherwise the best individual score of the steps is used, which is
    what the plan says about doing them one at a time.
    """
    selected = {str(item) for item in (active_ids or [])}
    published = int(score_block.get("published_score") or 0)
    moves = _moves_of(score_block)
    combos = _combos_of(score_block)

    power_ups: list[PowerUp] = []
    for move in moves:
        identifier = slug_of(str(move.get("title")))
        power_ups.append(
            PowerUp(
                id=identifier,
                title=str(move.get("title")),
                action=str(move.get("action") or ""),
                score_before=int(move.get("score_before") or published),
                score_after=int(move.get("score_after") or published),
                active=identifier in selected,
            )
        )

    active_moves = [power_up for power_up in power_ups if power_up.active]
    active_titles = {power_up.title for power_up in active_moves}

    score_simulated = published
    if active_moves:
        exact = [
            combo
            for combo in combos
            if {str(title) for title in combo.get("moves") or []} == active_titles
        ]
        if exact:
            score_simulated = max(int(combo.get("score_after") or published) for combo in exact)
        else:
            score_simulated = max(power_up.score_after for power_up in active_moves)

    synergy_detected = False
    synergy_score = published
    for combo in combos:
        titles = {str(title) for title in combo.get("moves") or []}
        if len(titles) < 2:
            continue
        after = int(combo.get("score_after") or published)
        individual = max(
            (
                int(move.get("score_after") or published)
                for move in moves
                if str(move.get("title")) in titles
            ),
            default=published,
        )
        if after > individual:
            synergy_detected = True
            synergy_score = max(synergy_score, after)

    return Simulation(
        score_base=published,
        score_simulated=score_simulated,
        score_delta=score_simulated - published,
        synergy_detected=synergy_detected and bool(active_moves),
        synergy_score=synergy_score,
        power_ups=power_ups,
        active_ids=[power_up.id for power_up in active_moves],
        active_titles=sorted(active_titles),
    )


def caps_of(score_block: dict[str, Any]) -> list[dict[str, Any]]:
    """The limits the plan puts on the score, and what removes them."""
    caps = score_block.get("caps_applied") or []
    return [cap for cap in caps if isinstance(cap, dict)]
