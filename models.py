from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from datetime import datetime


class Market(BaseModel):
    ticker: str
    event_ticker: str
    title: str
    yes_bid: float = Field(..., description="Best yes bid in dollars (0-1)")
    yes_ask: float = Field(..., description="Best yes ask in dollars (0-1)")
    last_price: Optional[float] = None
    volume: float = 0.0
    volume_24h: float = 0.0
    open_interest: float = 0.0
    close_time: Optional[datetime] = None
    series_ticker: Optional[str] = None

    @computed_field
    @property
    def mid_price(self) -> float:
        if self.yes_bid and self.yes_ask and self.yes_bid > 0:
            return (self.yes_bid + self.yes_ask) / 2
        if self.last_price and self.last_price > 0:
            return self.last_price
        return self.yes_bid or 0.5

    @computed_field
    @property
    def spread(self) -> float:
        return max(0.0, self.yes_ask - self.yes_bid)


class Leg(BaseModel):
    market: Market
    side: str = "yes"


class Combo(BaseModel):
    legs: List[Leg]
    estimated_prob: float
    payout_multiple: float
    liquidity_score: float
    spread_penalty: float
    correlation_penalty: float
    score: float
    category: str = "core"  # "core" or "upside"

    @computed_field
    @property
    def num_legs(self) -> int:
        return len(self.legs)

    def summary(self) -> str:
        parts = []
        for leg in self.legs:
            title = leg.market.title
            if len(title) > 55:
                title = title[:52] + "..."
            parts.append(f"{title} ({leg.market.mid_price:.0%})")
        return "  +  ".join(parts)

    def short_summary(self) -> str:
        return " + ".join(
            f"{leg.market.title[:40]} ({leg.market.mid_price:.0%})"
            for leg in self.legs
        )


class ComboResponse(BaseModel):
    rank: int
    payout_multiple: float
    estimated_prob: float
    num_legs: int
    score: float
    category: str
    summary: str
    legs: List[dict]


class DailyCombosResponse(BaseModel):
    generated_at: datetime
    core_count: int
    upside_count: int
    core: List[ComboResponse]
    upside: List[ComboResponse]
    markets_scanned: int
    candidates_generated: int