import datetime
import os
from typing import Annotated

import pandas as pd
import requests
from langchain_core.tools import tool

from tradingagents.dataflows.calculate_indicators import calculate_indicators, generate_builtin_quant_signals


BINANCE_BASE_URL = "https://api.binance.com"
FETCH_TIMEOUT_SECONDS = 10

# Common symbol aliases used by other venues or users.
BASE_ASSET_ALIASES = {
    "XBT": "BTC",
}

QUOTE_ASSET_ALIASES = {
    "USD": "USDT",
}

SUPPORTED_INTERVALS = {
    "minute": "1m",
    "hour": "1h",
    "day": "1d",
    "1m": "1m",
    "1h": "1h",
    "1d": "1d",
}


def _data_cache_dir() -> str:
    return os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")


def _normalize_binance_pair(pair: str) -> tuple[str, str]:
    raw = str(pair or "").upper().strip()
    if not raw:
        raise ValueError("pair cannot be empty")

    if "/" in raw:
        base, quote = raw.split("/", 1)
    else:
        merged = raw.replace("-", "")
        if merged.endswith("USDT"):
            base, quote = merged[:-4], "USDT"
        elif merged.endswith("USDC"):
            base, quote = merged[:-4], "USDC"
        elif merged.endswith("BUSD"):
            base, quote = merged[:-4], "BUSD"
        elif merged.endswith("USD"):
            base, quote = merged[:-3], "USD"
        elif merged.endswith("BTC"):
            base, quote = merged[:-3], "BTC"
        else:
            # Last-resort fallback for symbols like BTC -> BTC/USDT.
            base, quote = merged, "USDT"

    base = BASE_ASSET_ALIASES.get(base, base)
    quote = QUOTE_ASSET_ALIASES.get(quote, quote)

    symbol = f"{base}{quote}"
    canonical_pair = f"{base}/{quote}"
    return symbol, canonical_pair


def _klines_to_frame(rows: list[list]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    frame["timestamp"] = (pd.to_numeric(frame["open_time"], errors="coerce") // 1000).astype("Int64")
    frame["datetime"] = pd.to_datetime(frame["timestamp"], unit="s", errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.dropna(subset=["datetime", "open", "high", "low", "close", "volume", "timestamp"])
    frame["timestamp"] = frame["timestamp"].astype(int)
    frame = frame[["datetime", "open", "high", "low", "close", "volume", "timestamp"]]
    frame = frame.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    return frame.reset_index(drop=True)


def _write_pair_alias_meta(requested_pair: str, symbol: str, canonical_pair: str) -> None:
    data_cache_dir = _data_cache_dir()
    safe_requested = requested_pair.replace("/", "_")
    path = os.path.join(data_cache_dir, f"{safe_requested}_binance_alias.json")
    payload = {
        "requested_pair": requested_pair,
        "resolved_symbol": symbol,
        "resolved_pair": canonical_pair,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    os.makedirs(data_cache_dir, exist_ok=True)
    pd.Series(payload).to_json(path, force_ascii=False, indent=2)


@tool
def get_binance_ohlcv(
    pair: Annotated[str, "Trading pair or symbol, e.g. XBTUSD, BTCUSDT, BTC/USDT"],
    tradedate: Annotated[str, "Date time before which data is requested, format 'YYYY-MM-DD HH:MM:SS'"],
    timeframe: Annotated[str, "OHLCV timeframe: minute, hour, day, or 1m/1h/1d"] = "hour",
    limit: Annotated[int, "Number of rows to fetch, max 1000"] = 300,
) -> pd.DataFrame:
    """Fetch OHLCV from Binance Spot and persist to local cache for downstream indicators."""
    symbol, canonical_pair = _normalize_binance_pair(pair)
    interval = SUPPORTED_INTERVALS.get(str(timeframe).lower())
    if interval is None:
        raise ValueError("timeframe must be one of minute/hour/day/1m/1h/1d")

    try:
        end_ms = int(pd.to_datetime(tradedate).timestamp() * 1000)
    except Exception as exc:
        raise ValueError(f"failed to parse tradedate: {exc}") from exc

    req_limit = max(1, min(int(limit), 1000))

    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": req_limit,
        "endTime": end_ms,
    }

    response = requests.get(url, params=params, timeout=FETCH_TIMEOUT_SECONDS)
    response.raise_for_status()
    rows = response.json()

    frame = _klines_to_frame(rows)
    if frame.empty:
        return frame

    data_cache_dir = _data_cache_dir()
    prices_dir = os.path.join(data_cache_dir, "prices")
    os.makedirs(prices_dir, exist_ok=True)

    # Persist under resolved Binance symbol so indicator tools can load directly.
    price_path = os.path.join(prices_dir, f"{symbol}_ohlcv.csv")
    frame.to_csv(price_path, index=False)

    _write_pair_alias_meta(requested_pair=pair, symbol=symbol, canonical_pair=canonical_pair)
    return frame


@tool
def get_binance_indicators(
    pair: Annotated[str, "Trading pair or symbol, e.g. XBTUSD, BTCUSDT, BTC/USDT"],
    indicators: Annotated[list[str], "The list of indicators to calculate"],
) -> pd.DataFrame:
    """Calculate indicators from cached Binance OHLCV data."""
    symbol, _ = _normalize_binance_pair(pair)
    return calculate_indicators(pair=symbol, indicators=indicators)


@tool
def get_binance_builtin_quant_signals(
    pair: Annotated[str, "Trading pair or symbol, e.g. XBTUSD, BTCUSDT, BTC/USDT"],
) -> dict:
    """Generate built-in quant signals from cached Binance OHLCV data."""
    symbol, _ = _normalize_binance_pair(pair)
    return generate_builtin_quant_signals(pair=symbol)
