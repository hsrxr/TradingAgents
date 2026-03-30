import requests
import pandas as pd
import json
import os
import datetime
from typing import Annotated
from langchain_core.tools import tool
from tradingagents.dataflows.address_mapping import AERODROME_PAIRS


IDEAL_WARMUP = 200
API_MAX_LIMIT = 1000
INITIAL_BACKFILL_REQUESTS = 5
FETCH_TIMEOUT_SECONDS = 10


def _data_cache_dir() -> str:
    return os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")


def _paths_for_pair(pair: str):
    data_cache_dir = _data_cache_dir()
    prices_dir = os.path.join(data_cache_dir, "prices")
    indicators_dir = os.path.join(data_cache_dir, "indicators")
    os.makedirs(prices_dir, exist_ok=True)
    os.makedirs(indicators_dir, exist_ok=True)
    safe_pair = pair.replace("/", "_")
    return {
        "price_csv": os.path.join(prices_dir, f"{safe_pair}_ohlcv.csv"),
        "meta_json": os.path.join(data_cache_dir, f"{safe_pair}_meta.json"),
        "indicators_csv": os.path.join(indicators_dir, f"{safe_pair}_1h_indicators.csv"),
    }


def _safe_to_datetime(value: str) -> int:
    dt_obj = pd.to_datetime(value)
    return int(dt_obj.timestamp())


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    if "timestamp" not in out.columns:
        raise ValueError("OHLCV data missing timestamp column")

    out["timestamp"] = pd.to_numeric(out["timestamp"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["timestamp"]).copy()
    out["timestamp"] = out["timestamp"].astype(int)

    if "datetime" in out.columns:
        out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    else:
        out["datetime"] = pd.to_datetime(out["timestamp"], unit="s")

    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["open", "high", "low", "close", "volume", "datetime"])
    out = out[["datetime", "open", "high", "low", "close", "volume", "timestamp"]]
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    return out.reset_index(drop=True)


def _read_local_ohlcv(price_csv: str) -> pd.DataFrame:
    if not os.path.exists(price_csv):
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])
    try:
        df = pd.read_csv(price_csv, parse_dates=["datetime"])
        return _normalize_ohlcv(df)
    except Exception:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])


def _write_local_ohlcv(price_csv: str, df: pd.DataFrame) -> None:
    normalized = _normalize_ohlcv(df)
    normalized.to_csv(price_csv, index=False)


def _frame_signature(df: pd.DataFrame):
    if df.empty:
        return (0, None, None)
    return (int(len(df)), int(df["timestamp"].min()), int(df["timestamp"].max()))


def _fetch_geckoterminal_chunk(pair: str, timeframe: str, before_timestamp: int, limit: int) -> pd.DataFrame:
    url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{AERODROME_PAIRS[pair]}/ohlcv/{timeframe}"
    params = {
        "limit": min(limit, API_MAX_LIMIT),
        "before_timestamp": before_timestamp,
        "token": "quote",
        "currency": "token",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    response = requests.get(url, headers=headers, params=params, timeout=FETCH_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    ohlcv_list = payload.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
    if not ohlcv_list:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

    df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    return _normalize_ohlcv(df)


def _merge_frames(base_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    if base_df.empty:
        return _normalize_ohlcv(new_df)
    if new_df.empty:
        return _normalize_ohlcv(base_df)
    merged = pd.concat([base_df, new_df], ignore_index=True)
    return _normalize_ohlcv(merged)


def _compute_actual_warmup(limit: int) -> int:
    if limit + IDEAL_WARMUP <= API_MAX_LIMIT:
        return IDEAL_WARMUP
    return max(0, API_MAX_LIMIT - limit)


def _slice_for_request(df: pd.DataFrame, before_timestamp: int, limit: int) -> pd.DataFrame:
    eligible = df[df["timestamp"] <= before_timestamp]
    if eligible.empty:
        return eligible.copy()
    return eligible.tail(limit).reset_index(drop=True)


def _backfill_initial_history(pair: str, timeframe: str, before_timestamp: int) -> pd.DataFrame:
    merged = pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])
    cursor = before_timestamp
    for _ in range(INITIAL_BACKFILL_REQUESTS):
        chunk = _fetch_geckoterminal_chunk(pair, timeframe, cursor, API_MAX_LIMIT)
        if chunk.empty:
            break
        prev_len = len(merged)
        merged = _merge_frames(merged, chunk)
        if len(merged) == prev_len:
            break
        oldest_ts = int(chunk["timestamp"].min())
        cursor = oldest_ts - 1
    return merged


def _ensure_data_coverage(pair: str, timeframe: str, before_timestamp: int, needed_total: int, local_df: pd.DataFrame) -> pd.DataFrame:
    df = local_df.copy()

    # 先补最近区间，避免本地库落后于请求日期。
    need_recent_refresh = df.empty or int(df["timestamp"].max()) < (before_timestamp - 3600)
    if need_recent_refresh:
        recent_chunk = _fetch_geckoterminal_chunk(pair, timeframe, before_timestamp, API_MAX_LIMIT)
        df = _merge_frames(df, recent_chunk)

    # 若在请求时点之前仍然不够，向更老历史回填。
    max_backfill_rounds = 10
    rounds = 0
    while len(df[df["timestamp"] <= before_timestamp]) < needed_total and rounds < max_backfill_rounds:
        eligible = df[df["timestamp"] <= before_timestamp]
        if eligible.empty:
            cursor = before_timestamp
        else:
            cursor = int(eligible["timestamp"].min()) - 1

        older_chunk = _fetch_geckoterminal_chunk(pair, timeframe, cursor, API_MAX_LIMIT)
        if older_chunk.empty:
            break

        prev_len = len(df)
        df = _merge_frames(df, older_chunk)
        if len(df) == prev_len:
            break
        rounds += 1

    return df


def _write_meta(meta_path: str, payload: dict) -> None:
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def _is_recent_data_stale(df: pd.DataFrame, before_timestamp: int) -> bool:
    if df.empty:
        return True
    latest_ts = int(df["timestamp"].max())
    # For 1h bars, if local latest is older than requested horizon by >1h,
    # force a recent refresh even when row-count coverage is enough.
    return latest_ts < (before_timestamp - 3600)


@tool
def get_dex_ohlcv(
    pair: Annotated[str, "Trading pair name, such as 'WETH/USDC'"],
    tradedate: Annotated[str, "Date and time before which data is requested, format 'YYYY-MM-DD HH:MM:SS'"],
    timeframe: Annotated[str, "OHLCV timeframe: day, hour, minute"] = "hour",
    limit: Annotated[int, "Number of OHLCV rows to return, max 1000"] = 100,
) -> pd.DataFrame:
    """
    获取指定流动性池的历史 OHLCV 时间序列数据，并注入预热长度到全局状态。
    """
    if pair not in AERODROME_PAIRS:
        raise ValueError(f"❌ 交易对 {pair} 的池地址未配置，请检查 address_mapping.py 中的 AERODROME_PAIRS 字典")

    try:
        before_timestamp = _safe_to_datetime(tradedate)
    except Exception as e:
        raise ValueError(f"❌ 解析 tradedate 失败，请检查时间格式: {e}")

    if limit <= 0:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

    if timeframe != "hour":
        # 非 1h 请求保持原有在线获取行为；本地长期库仅维护 1h。
        try:
            return _fetch_geckoterminal_chunk(pair, timeframe, before_timestamp, limit)
        except requests.exceptions.RequestException as e:
            print(f"请求 GeckoTerminal API 失败: {e}")
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

    requested_limit = int(limit)
    actual_warmup = _compute_actual_warmup(requested_limit)
    needed_total = requested_limit + actual_warmup

    paths = _paths_for_pair(pair)
    price_csv = paths["price_csv"]
    meta_path = paths["meta_json"]

    local_df = _read_local_ohlcv(price_csv)
    before_sig = _frame_signature(local_df)

    try:
        # 新标的：首次尽可能多拉取 1h 历史，建立本地数据库。
        if local_df.empty:
            local_df = _backfill_initial_history(pair, "hour", before_timestamp)

        # 如果当前请求不是本地库子集，或本地最近数据明显落后于请求时点，则增量拉取并合并。
        needs_more_rows = len(local_df[local_df["timestamp"] <= before_timestamp]) < needed_total
        needs_recent_refresh = _is_recent_data_stale(local_df, before_timestamp)
        if needs_more_rows or needs_recent_refresh:
            local_df = _ensure_data_coverage(
                pair=pair,
                timeframe="hour",
                before_timestamp=before_timestamp,
                needed_total=needed_total,
                local_df=local_df,
            )

        if local_df.empty:
            print("未获取到有效的 OHLCV 数据，请检查地址或网络。")
            return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

        after_sig = _frame_signature(local_df)
        if (not os.path.exists(price_csv)) or (after_sig != before_sig):
            _write_local_ohlcv(price_csv, local_df)

        eligible = local_df[local_df["timestamp"] <= before_timestamp]
        available_total = len(eligible)
        effective_warmup = min(actual_warmup, max(0, available_total - requested_limit))
        agent_rows = eligible.tail(requested_limit).reset_index(drop=True)

        _write_meta(
            meta_path,
            {
                "actual_warmup": int(effective_warmup),
                "agent_limit": int(requested_limit),
                "total_fetched": int(available_total),
                "db_total_rows": int(len(local_df)),
                "timeframe": "hour",
                "cache_updated_at": datetime.datetime.utcnow().isoformat(),
                "price_db_path": price_csv,
                "indicators_db_path": paths["indicators_csv"],
            },
        )

        return agent_rows
    except requests.exceptions.RequestException as e:
        print(f"请求 GeckoTerminal API 失败: {e}")
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "timestamp"])

if __name__ == "__main__":
    PAIR = "WETH/USDC"
    
    # 模拟 Agent 在过去的某个时刻请求数据
    TRADEDATE = "2026-03-29 00:00:00" 
    AGENT_LIMIT = 100
    
    # print(f"正在拉取 {TRADEDATE} 之前的数据 (Agent 需 {AGENT_LIMIT} 根，系统额外拉取预热数据)...")
    
    df_agent_data = get_dex_ohlcv.invoke(
        {
            "pair": PAIR,
            "tradedate": TRADEDATE,
            "timeframe": "hour",
            "limit": AGENT_LIMIT,
        }
    )
    
    if not df_agent_data.empty:
        print(f"\n✅ 成功获取！只给 Agent 返回了请求的 {len(df_agent_data)} 条记录。")
        print("\nAgent 看到的最后 5 条记录（确保没有超过 TRADEDATE):")
        print(df_agent_data.tail())