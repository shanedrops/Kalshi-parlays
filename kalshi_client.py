"""
Kalshi public market data client.
No authentication required for these endpoints.
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from models import Market
import time
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

# High-value sports series. Expand over time.
PRIORITY_SERIES = [
    "KXNFLGAME",
    "KXNFLSPREAD",
    "KXNFLTOTAL",
    "KXNBAGAME",
    "KXNBASPREAD",
    "KXNBATOTAL",
    "KXMLBGAME",
    "KXMLBSPREAD",
    "KXNHLGAME",
    "KXNHLSPREAD",
    "KXNCAAFGAME",
    "KXNCAABGAME",
]


def _parse_market(raw: dict, series_ticker: str) -> Optional[Market]:
    try:
        yes_bid = float(raw.get("yes_bid_dollars") or 0)
        yes_ask = float(raw.get("yes_ask_dollars") or 0)
        last = None
        if raw.get("last_price_dollars"):
            last = float(raw["last_price_dollars"])

        volume = float(raw.get("volume_fp") or 0)
        volume_24h = float(raw.get("volume_24h_fp") or 0)
        oi = float(raw.get("open_interest_fp") or 0)

        close_time = None
        if raw.get("close_time"):
            close_time = datetime.fromisoformat(
                raw["close_time"].replace("Z", "+00:00")
            )

        title = (
            raw.get("title")
            or raw.get("yes_sub_title")
            or raw.get("subtitle")
            or raw["ticker"]
        )

        return Market(
            ticker=raw["ticker"],
            event_ticker=raw["event_ticker"],
            title=title,
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            last_price=last,
            volume=volume,
            volume_24h=volume_24h,
            open_interest=oi,
            close_time=close_time,
            series_ticker=series_ticker,
        )
    except Exception as e:
        logger.debug(f"Failed to parse market: {e}")
        return None


def get_markets(
    status: str = "open",
    series_tickers: Optional[List[str]] = None,
    max_pages_per_series: int = 8,
    min_volume: float = 0.0,
    max_spread: float = 0.28,
) -> List[Market]:
    """
    Fetch open sports markets from priority series.
    Soft quality filters so results still appear on quieter days.
    """
    series_tickers = series_tickers or PRIORITY_SERIES
    markets: List[Market] = []
    seen_tickers = set()

    for series in series_tickers:
        cursor = None
        pages = 0

        while pages < max_pages_per_series:
            params = {
                "status": status,
                "series_ticker": series,
                "limit": 1000,
            }
            if cursor:
                params["cursor"] = cursor

            try:
                resp = requests.get(
                    f"{BASE_URL}/markets", params=params, timeout=12
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning(f"Error fetching series {series}: {e}")
                break

            batch = data.get("markets", [])
            if not batch:
                break

            for raw in batch:
                m = _parse_market(raw, series)
                if not m:
                    continue
                if m.ticker in seen_tickers:
                    continue

                if m.yes_bid <= 0.05 or m.yes_ask >= 0.95:
                    continue
                if m.spread > max_spread:
                    continue
                if min_volume > 0 and m.volume < min_volume and m.volume_24h < min_volume:
                    continue

                seen_tickers.add(m.ticker)
                markets.append(m)

            cursor = data.get("cursor")
            if not cursor:
                break
            pages += 1
            time.sleep(0.1)

    logger.info(f"Fetched {len(markets)} markets across {len(series_tickers)} series")
    return markets


def get_todays_markets(
    hours_ahead: int = 96,
    min_volume: float = 0.0,
) -> List[Market]:
    """Return markets closing within the next N hours (default ~4 days)."""
    all_markets = get_markets(min_volume=min_volume)
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours_ahead)

    todays = []
    for m in all_markets:
        if m.close_time is None:
            todays.append(m)
        elif now < m.close_time <= cutoff:
            todays.append(m)

    todays.sort(key=lambda m: (m.volume_24h + m.volume), reverse=True)
    return todays
