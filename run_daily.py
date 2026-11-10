#!/usr/bin/env python3
"""
Simple CLI runner – useful for testing without starting the API server.
"""

from kalshi_client import get_todays_markets
from generator import generate_combos
from ranker import rank_and_split
import json
from datetime import datetime, timezone


def main():
    print("=" * 60)
    print("Kalshi Daily Combos Generator")
    print("=" * 60)

    print("\n→ Fetching markets...")
    markets = get_todays_markets(hours_ahead=96, min_volume=0.0)
    print(f"  Found {len(markets)} usable markets")

    if len(markets) < 6:
        print("Not enough liquid markets right now. Try again later.")
        return

    print("\n→ Generating candidates (this may take 10–40 seconds)...")
    candidates = generate_combos(
        markets,
        min_legs=2,
        max_legs=4,
        max_candidates=10000,
        pool_size=min(90, len(markets)),
    )
    print(f"  Generated {len(candidates)} candidates")

    core, upside = rank_and_split(
        candidates,
        core_count=18,
        upside_count=5,
    )

    print("\n" + "=" * 60)
    print("CORE LIST  (Highest chance of winning → lower)")
    print("Target: 2–4.6× payout")
    print("=" * 60)
    for i, c in enumerate(core, 1):
        print(
            f"{i:2d}. {c.payout_multiple:5.2f}x   "
            f"Prob {c.estimated_prob:5.1%}   "
            f"Legs:{c.num_legs}   "
            f"{c.short_summary()}"
        )

    print("\n" + "=" * 60)
    print("HIGHER UPSIDE  (5–11×)")
    print("=" * 60)
    if not upside:
        print("  (No qualifying upside combos found)")
    for i, c in enumerate(upside, 1):
        print(
            f"{i:2d}. {c.payout_multiple:5.2f}x   "
            f"Prob {c.estimated_prob:5.1%}   "
            f"Legs:{c.num_legs}   "
            f"{c.short_summary()}"
        )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": len(markets),
        "candidates": len(candidates),
        "core": [
            {
                "rank": i,
                "payout": round(c.payout_multiple, 2),
                "prob": round(c.estimated_prob, 4),
                "summary": c.summary(),
                "tickers": [leg.market.ticker for leg in c.legs],
            }
            for i, c in enumerate(core, 1)
        ],
        "upside": [
            {
                "rank": i,
                "payout": round(c.payout_multiple, 2),
                "prob": round(c.estimated_prob, 4),
                "summary": c.summary(),
                "tickers": [leg.market.ticker for leg in c.legs],
            }
            for i, c in enumerate(upside, 1)
        ],
    }

    with open("daily_combos.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved results to daily_combos.json")
    print(f"  Core: {len(core)} | Upside: {len(upside)}")


if __name__ == "__main__":
    main()
