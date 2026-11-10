"""
Ranking and splitting logic.
"""

from typing import List, Tuple
from models import Combo
import logging

logger = logging.getLogger(__name__)


def rank_and_split(
    candidates: List[Combo],
    core_min_payout: float = 2.0,
    core_max_payout: float = 4.6,
    upside_min_payout: float = 5.0,
    upside_max_payout: float = 11.0,
    core_count: int = 18,
    upside_count: int = 5,
) -> Tuple[List[Combo], List[Combo]]:
    """
    Split candidates into two lists:

    - Core: 2–4.6× payout, sorted by estimated probability (highest chance first)
    - Upside: 5–11× payout, sorted by overall score
    """
    core: List[Combo] = []
    upside: List[Combo] = []

    for c in candidates:
        if core_min_payout <= c.payout_multiple <= core_max_payout:
            c.category = "core"
            core.append(c)
        elif upside_min_payout <= c.payout_multiple <= upside_max_payout:
            c.category = "upside"
            upside.append(c)

    # Core: safest first (highest estimated probability)
    core_sorted = sorted(
        core, key=lambda x: (x.estimated_prob, x.score), reverse=True
    )[:core_count]

    # Upside: best overall quality among riskier combos
    upside_sorted = sorted(
        upside, key=lambda x: x.score, reverse=True
    )[:upside_count]

    logger.info(
        f"Ranked → Core: {len(core_sorted)}, Upside: {len(upside_sorted)}"
    )
    return core_sorted, upside_sorted


def to_response_format(
    combos: List[Combo], start_rank: int = 1
) -> list:
    """Convert Combo objects into clean API-friendly dicts."""
    results = []
    for i, c in enumerate(combos, start=start_rank):
        results.append(
            {
                "rank": i,
                "payout_multiple": round(c.payout_multiple, 2),
                "estimated_prob": round(c.estimated_prob, 4),
                "num_legs": c.num_legs,
                "score": c.score,
                "category": c.category,
                "summary": c.summary(),
                "legs": [
                    {
                        "ticker": leg.market.ticker,
                        "title": leg.market.title,
                        "mid_price": round(leg.market.mid_price, 3),
                        "yes_bid": round(leg.market.yes_bid, 3),
                        "yes_ask": round(leg.market.yes_ask, 3),
                        "volume_24h": round(leg.market.volume_24h, 1),
                        "event_ticker": leg.market.event_ticker,
                    }
                    for leg in c.legs
                ],
            }
        )
    return results