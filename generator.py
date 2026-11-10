"""
Combo generation logic.
Produces candidate multi-leg combinations from a pool of markets.
"""

from itertools import combinations
from typing import List
from models import Market, Leg, Combo
import math
import logging

logger = logging.getLogger(__name__)


def generate_combos(
    markets: List[Market],
    min_legs: int = 2,
    max_legs: int = 4,
    max_candidates: int = 12000,
    pool_size: int = 90,
) -> List[Combo]:
    """
    Generate candidate combos.

    Strategy:
    - Prefer higher-liquidity markets
    - Allow limited same-event combinations (mostly for 2-leg)
    - Filter extreme probabilities early
    """
    if len(markets) < min_legs:
        logger.warning("Not enough markets to generate combos")
        return []

    # Take the most liquid markets as the working pool
    pool = sorted(
        markets, key=lambda m: (m.volume_24h + m.volume), reverse=True
    )[:pool_size]

    candidates: List[Combo] = []

    for n_legs in range(min_legs, max_legs + 1):
        for combo_markets in combinations(pool, n_legs):
            event_tickers = [m.event_ticker for m in combo_markets]
            unique_events = len(set(event_tickers))

            # Correlation control
            # Allow fully independent or one shared event for 2-leg
            if n_legs >= 3 and unique_events < n_legs - 1:
                continue
            if n_legs == 2 and unique_events == 1:
                # same-game 2-leg is allowed (e.g. winner + total)
                pass

            legs = [Leg(market=m, side="yes") for m in combo_markets]

            probs = [leg.market.mid_price for leg in legs]
            estimated_prob = math.prod(probs)

            # Hard filters on probability
            if estimated_prob < 0.04 or estimated_prob > 0.55:
                continue

            payout = 1.0 / estimated_prob

            # Liquidity score (log scale so big volume doesn't dominate)
            volumes = [
                max(leg.market.volume_24h, leg.market.volume, 10.0)
                for leg in legs
            ]
            liquidity_score = sum(math.log10(v) for v in volumes) / len(volumes)

            # Average spread
            spreads = [leg.market.spread for leg in legs]
            spread_penalty = sum(spreads) / len(spreads)

            # Correlation penalty
            correlation_penalty = max(0.0, (n_legs - unique_events) * 0.18)

            score = (
                estimated_prob
                * liquidity_score
                / (1.0 + spread_penalty * 4.0 + correlation_penalty)
            )

            candidates.append(
                Combo(
                    legs=legs,
                    estimated_prob=estimated_prob,
                    payout_multiple=payout,
                    liquidity_score=round(liquidity_score, 3),
                    spread_penalty=round(spread_penalty, 4),
                    correlation_penalty=round(correlation_penalty, 3),
                    score=round(score, 5),
                    category="temp",
                )
            )

            if len(candidates) >= max_candidates:
                break

        if len(candidates) >= max_candidates:
            break

    logger.info(f"Generated {len(candidates)} candidate combos")
    return candidates