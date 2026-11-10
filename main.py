"""
FastAPI application for Kalshi daily parlays / combos.
Includes in-memory caching so expensive generation runs only every few minutes.
"""

from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
import logging
import threading
from typing import Optional, Dict, Any

from kalshi_client import get_todays_markets
from generator import generate_combos
from ranker import rank_and_split, to_response_format
from models import DailyCombosResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Kalshi Daily Parlays",
    description="Generates ranked daily combos (2-4x core + 5-10x upside) from Kalshi sports markets",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Simple in-memory cache
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 12 * 60  # 12 minutes

_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {
    "data": None,           # DailyCombosResponse or dict
    "generated_at": None,   # datetime
    "params_key": None,     # str key of the params used
}


def _make_cache_key(core_count: int, upside_count: int, hours_ahead: int, min_volume: float) -> str:
    return f"{core_count}:{upside_count}:{hours_ahead}:{min_volume}"


def _is_cache_valid(params_key: str) -> bool:
    with _cache_lock:
        if _cache["data"] is None or _cache["generated_at"] is None:
            return False
        if _cache["params_key"] != params_key:
            return False
        age = (datetime.now(timezone.utc) - _cache["generated_at"]).total_seconds()
        return age < CACHE_TTL_SECONDS


def _set_cache(params_key: str, response: DailyCombosResponse) -> None:
    with _cache_lock:
        _cache["data"] = response
        _cache["generated_at"] = datetime.now(timezone.utc)
        _cache["params_key"] = params_key
        logger.info(f"Cache updated (TTL={CACHE_TTL_SECONDS}s)")


def _get_cache() -> Optional[DailyCombosResponse]:
    with _cache_lock:
        return _cache["data"]


def _cache_age_seconds() -> Optional[float]:
    with _cache_lock:
        if _cache["generated_at"] is None:
            return None
        return (datetime.now(timezone.utc) - _cache["generated_at"]).total_seconds()


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------
def _generate_combos(
    core_count: int = 18,
    upside_count: int = 5,
    hours_ahead: int = 96,
    min_volume: float = 0.0,
) -> DailyCombosResponse:
    logger.info("Starting combo generation...")

    markets = get_todays_markets(hours_ahead=hours_ahead, min_volume=min_volume)
    logger.info(f"Markets available: {len(markets)}")

    if len(markets) < 6:
        return DailyCombosResponse(
            generated_at=datetime.now(timezone.utc),
            core_count=0,
            upside_count=0,
            core=[],
            upside=[],
            markets_scanned=len(markets),
            candidates_generated=0,
        )

    candidates = generate_combos(
        markets,
        min_legs=2,
        max_legs=4,
        max_candidates=12000,
        pool_size=min(100, len(markets)),
    )

    core, upside = rank_and_split(
        candidates,
        core_count=core_count,
        upside_count=upside_count,
    )

    return DailyCombosResponse(
        generated_at=datetime.now(timezone.utc),
        core_count=len(core),
        upside_count=len(upside),
        core=to_response_format(core),
        upside=to_response_format(upside),
        markets_scanned=len(markets),
        candidates_generated=len(candidates),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    age = _cache_age_seconds()
    return {
        "message": "Kalshi Daily Parlays API",
        "version": "0.2.0",
        "docs": "/docs",
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cache_age_seconds": round(age, 1) if age is not None else None,
        "endpoints": {
            "today": "/combos/today",
            "health": "/health",
            "cache_status": "/cache/status",
        },
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache_age_seconds": _cache_age_seconds(),
    }


@app.get("/cache/status")
def cache_status():
    with _cache_lock:
        return {
            "has_data": _cache["data"] is not None,
            "generated_at": _cache["generated_at"].isoformat() if _cache["generated_at"] else None,
            "age_seconds": _cache_age_seconds(),
            "ttl_seconds": CACHE_TTL_SECONDS,
            "params_key": _cache["params_key"],
            "is_valid": _is_cache_valid(_cache["params_key"]) if _cache["params_key"] else False,
        }


@app.get("/combos/today", response_model=DailyCombosResponse)
def get_todays_combos(
    core_count: int = Query(18, ge=5, le=40),
    upside_count: int = Query(5, ge=0, le=15),
    hours_ahead: int = Query(96, ge=12, le=168),
    min_volume: float = Query(0.0, ge=0),
    force_refresh: bool = Query(False, description="Bypass cache and regenerate"),
):
    """
    Generate today's ranked combos.

    - **core**: Highest chance of winning first (2–4.6× payout)
    - **upside**: Higher risk / higher reward (5–11× payout)

    Results are cached for 12 minutes. Use `force_refresh=true` to regenerate.
    """
    params_key = _make_cache_key(core_count, upside_count, hours_ahead, min_volume)

    if not force_refresh and _is_cache_valid(params_key):
        logger.info("Serving from cache")
        cached = _get_cache()
        return cached

    # Generate fresh
    response = _generate_combos(
        core_count=core_count,
        upside_count=upside_count,
        hours_ahead=hours_ahead,
        min_volume=min_volume,
    )
    _set_cache(params_key, response)
    return response


@app.get("/combos/core")
def get_core_only(
    count: int = Query(15, ge=5, le=30),
    force_refresh: bool = Query(False),
):
    """Convenience endpoint that returns only the core (highest probability) list."""
    full = get_todays_combos(
        core_count=count,
        upside_count=0,
        force_refresh=force_refresh,
    )
    return {
        "generated_at": full.generated_at,
        "count": full.core_count,
        "combos": full.core,
        "from_cache": not force_refresh and _is_cache_valid(
            _make_cache_key(count, 0, 96, 0.0)
        ),
    }


@app.post("/cache/clear")
def clear_cache():
    """Clear the in-memory cache (useful after deploy or for debugging)."""
    with _cache_lock:
        _cache["data"] = None
        _cache["generated_at"] = None
        _cache["params_key"] = None
    logger.info("Cache cleared")
    return {"status": "cleared"}
