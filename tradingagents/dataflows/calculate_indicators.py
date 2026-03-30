import os
import json
import pandas as pd
import numpy as np
from langchain_core.tools import tool
from typing import Annotated

from typing import List, Union, Callable, Dict, Optional


def _signal_from_value(value: float, threshold: float = 0.0) -> str:
    if pd.isna(value):
        return "NEUTRAL"
    if value > threshold:
        return "LONG"
    if value < -threshold:
        return "SHORT"
    return "NEUTRAL"


def _strength_from_value(value: float, scale: float) -> float:
    if pd.isna(value) or scale <= 0:
        return 0.0
    # Keep strength bounded in [0, 1] and robust to outliers.
    return float(np.clip(abs(value) / scale, 0.0, 1.0))


def _compute_builtin_quant_factors(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    close = df["close"]
    open_ = df["open"]
    volume = df["volume"]

    # Alpha#12: sign(delta(volume, 1)) * (-1 * delta(close, 1))
    alpha101_12 = np.sign(volume.diff(1)) * (-1.0 * close.diff(1))

    # Alpha#2 variant: -corr(delta(log(volume), 2), (close-open)/open, 6)
    log_vol = pd.Series(np.log(volume.replace(0, np.nan)), index=volume.index)
    dlog_vol_2 = log_vol.diff(2)
    intraday_ret = (close - open_) / open_.replace(0, np.nan)
    alpha101_2_variant = -1.0 * dlog_vol_2.rolling(window=6).corr(intraday_ret)

    # Jointquant 191 variant:
    # ((EMA(close, 12) - close[t-12]) / StdDev(close, 12)) * (volume / SMA(volume, 12))
    ema_12 = close.ewm(span=12, adjust=False).mean()
    close_lag_12 = close.shift(12)
    std_12 = close.rolling(window=12).std(ddof=0).replace(0, np.nan)
    vol_sma_12 = volume.rolling(window=12).mean().replace(0, np.nan)
    gtja_191_variant = ((ema_12 - close_lag_12) / std_12) * (volume / vol_sma_12)

    out["alpha101_12"] = alpha101_12
    out["alpha101_2_variant"] = alpha101_2_variant
    out["gtja_191_variant"] = gtja_191_variant
    out["datetime"] = df["datetime"]

    return out


def generate_builtin_quant_signals(pair: str) -> dict:
    df = load_price_data(pair)
    factor_df = _compute_builtin_quant_factors(df)

    latest = factor_df.iloc[-1]
    latest_dt = str(latest["datetime"]) if "datetime" in latest else None

    recent = factor_df.tail(60)
    alpha12_scale = float(recent["alpha101_12"].abs().median(skipna=True) or 0.0)
    alpha2_scale = float(recent["alpha101_2_variant"].abs().median(skipna=True) or 0.0)
    gtja_scale = float(recent["gtja_191_variant"].abs().median(skipna=True) or 0.0)

    alpha12_value = float(latest["alpha101_12"]) if pd.notna(latest["alpha101_12"]) else np.nan
    alpha2_value = float(latest["alpha101_2_variant"]) if pd.notna(latest["alpha101_2_variant"]) else np.nan
    gtja_value = float(latest["gtja_191_variant"]) if pd.notna(latest["gtja_191_variant"]) else np.nan

    factors = [
        {
            "name": "alpha101_12",
            "formula": "sign(delta(volume,1)) * (-delta(close,1))",
            "value": None if pd.isna(alpha12_value) else alpha12_value,
            "signal": _signal_from_value(alpha12_value),
            "strength_0_to_1": _strength_from_value(alpha12_value, alpha12_scale),
        },
        {
            "name": "alpha101_2_variant",
            "formula": "-corr(delta(log(volume),2), (close-open)/open, 6)",
            "value": None if pd.isna(alpha2_value) else alpha2_value,
            "signal": _signal_from_value(alpha2_value),
            "strength_0_to_1": _strength_from_value(alpha2_value, alpha2_scale),
        },
        {
            "name": "gtja_191_variant",
            "formula": "((EMA(close,12)-close[t-12])/StdDev(close,12))*(volume/SMA(volume,12))",
            "value": None if pd.isna(gtja_value) else gtja_value,
            "signal": _signal_from_value(gtja_value),
            "strength_0_to_1": _strength_from_value(gtja_value, gtja_scale),
        },
    ]

    numeric_values = [x for x in [alpha12_value, alpha2_value, gtja_value] if not pd.isna(x)]
    blended_value = float(np.mean(numeric_values)) if numeric_values else np.nan
    blended_scale = float(np.median(np.abs(numeric_values))) if numeric_values else 0.0

    return {
        "pair": pair,
        "latest_datetime": latest_dt,
        "factors": factors,
        "blended": {
            "value": None if pd.isna(blended_value) else blended_value,
            "signal": _signal_from_value(blended_value),
            "strength_0_to_1": _strength_from_value(blended_value, blended_scale),
        },
    }

def load_price_data(pair: str) -> pd.DataFrame:
    DATA_CACHE_DIR = os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")
    file_path = f"{DATA_CACHE_DIR}/prices/{pair.replace('/', '_')}_ohlcv.csv"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data cache not found: {file_path}")
    return pd.read_csv(file_path, parse_dates=['datetime'])


def _indicator_db_path(pair: str) -> str:
    data_cache_dir = os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")
    indicators_dir = os.path.join(data_cache_dir, "indicators")
    os.makedirs(indicators_dir, exist_ok=True)
    return os.path.join(indicators_dir, f"{pair.replace('/', '_')}_1h_indicators.csv")


def _build_full_indicator_db(df: pd.DataFrame) -> pd.DataFrame:
    # Persist a complete indicator table so repeated requests can reuse local database.
    full_results = {name: func(df) for name, func in INDICATOR_REGISTRY.items()}
    out = pd.DataFrame(full_results, index=df.index)
    out["datetime"] = df["datetime"].values
    out["timestamp"] = df["timestamp"].values
    return out


def _write_indicator_db(pair: str, indicator_df: pd.DataFrame) -> None:
    path = _indicator_db_path(pair)
    indicator_df.to_csv(path, index=False)


def load_warmup_len_from_meta(pair: str) -> int:
    """
    从 {pair}_meta.json 读取 warmup 长度。
    兼容两种字段: CURRENT_WARMUP_CANDLES / actual_warmup。
    """
    data_cache_dir = os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")
    meta_path = os.path.join(data_cache_dir, f"{pair.replace('/', '_')}_meta.json")

    if not os.path.exists(meta_path):
        return 0

    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        raw_value = meta.get("CURRENT_WARMUP_CANDLES", meta.get("actual_warmup", 0))
        return max(0, int(raw_value))
    except (json.JSONDecodeError, ValueError, TypeError, OSError):
        return 0

def calculate_indicators(pair: str, indicators: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
    """
    接收指标列表，按需计算并根据 CURRENT_WARMUP_CANDLES 截断预热数据后返回。
    """

    if indicators is None:
        indicators = ['close_50_sma', 'macd', 'rsi']
    elif isinstance(indicators, str):
        indicators = [indicators]
    elif not isinstance(indicators, (list, tuple, set, pd.Index, np.ndarray)):
        raise TypeError("indicators 必须是字符串或指标列表")

    indicators = list(dict.fromkeys(indicators))


    missing = [col for col in indicators if col not in INDICATOR_REGISTRY]
    if missing:
        raise ValueError(f"请求了不支持的指标: {missing}。当前支持: {list(INDICATOR_REGISTRY.keys())}")

    # 3. 获取全量数据上下文以确保计算精度

    df = load_price_data(pair)

    # 4. 全量计算并持久化 1h 指标数据库
    full_indicator_df = _build_full_indicator_db(df)
    _write_indicator_db(pair, full_indicator_df)

    # 5. 按请求指标选择返回子集
    result_df = full_indicator_df[indicators].copy()

    # 6. 从 meta 文件读取 warmup，并截断预热 K 线 (Warmup Truncation)
    warmup_len = load_warmup_len_from_meta(pair)
    
    if warmup_len > 0:
        # 防溢出：确保截断长度不会超过数据总长度
        safe_cut = min(warmup_len, len(result_df))
        result_df = result_df.iloc[safe_cut:].copy()

    # 7. 添加 datetime 列到返回结果
    result_df['datetime'] = full_indicator_df.loc[result_df.index, 'datetime'].values

    return result_df


INDICATOR_REGISTRY: Dict[str, Callable[[pd.DataFrame], pd.Series]] = {}

def register_indicator(name: str):
    def decorator(func: Callable[[pd.DataFrame], pd.Series]):
        INDICATOR_REGISTRY[name] = func
        return func
    return decorator



@register_indicator('close_50_sma')
def calc_close_50_sma(df: pd.DataFrame) -> pd.Series:
    return df['close'].rolling(window=50).mean()

@register_indicator('close_200_sma')
def calc_close_200_sma(df: pd.DataFrame) -> pd.Series:
    return df['close'].rolling(window=200).mean()

@register_indicator('close_10_ema')
def calc_close_10_ema(df: pd.DataFrame) -> pd.Series:
    return df['close'].ewm(span=10, adjust=False).mean()

def _get_macd_base(df: pd.DataFrame) -> pd.Series:
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    return ema_12 - ema_26

@register_indicator('macd')
def calc_macd(df: pd.DataFrame) -> pd.Series:
    return _get_macd_base(df)

@register_indicator('macds')
def calc_macds(df: pd.DataFrame) -> pd.Series:
    macd = _get_macd_base(df)
    return macd.ewm(span=9, adjust=False).mean()

@register_indicator('macdh')
def calc_macdh(df: pd.DataFrame) -> pd.Series:
    macd = _get_macd_base(df)
    macds = macd.ewm(span=9, adjust=False).mean()
    return macd - macds

@register_indicator('rsi')
def calc_rsi(df: pd.DataFrame) -> pd.Series:
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))
    return pd.Series(rsi, index=df.index)

def _get_boll_base(df: pd.DataFrame):
    mean = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std(ddof=0)
    return mean, std

@register_indicator('boll')
def calc_boll(df: pd.DataFrame) -> pd.Series:
    mean, _ = _get_boll_base(df)
    return mean

@register_indicator('boll_ub')
def calc_boll_ub(df: pd.DataFrame) -> pd.Series:
    mean, std = _get_boll_base(df)
    return mean + (2 * std)

@register_indicator('boll_lb')
def calc_boll_lb(df: pd.DataFrame) -> pd.Series:
    mean, std = _get_boll_base(df)
    return mean - (2 * std)

@register_indicator('atr')
def calc_atr(df: pd.DataFrame) -> pd.Series:
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/14, adjust=False).mean()

@register_indicator('vwma')
def calc_vwma(df: pd.DataFrame) -> pd.Series:
    window_vwma = 20
    price_vol = (df['close'] * df['volume']).rolling(window=window_vwma).sum()
    vol_sum = df['volume'].rolling(window=window_vwma).sum()
    return price_vol / vol_sum


@tool
def get_dex_indicators(
    pair: Annotated[str, "The trading pair for which to fetch indicators"],
    indicators: Annotated[List[str], "The list of indicators to calculate"],
):
    """LangChain tool wrapper over calculate_indicators for direct graph binding."""
    return calculate_indicators(pair=pair, indicators=indicators)


@tool
def get_builtin_quant_signals(
    pair: Annotated[str, "The trading pair for which to fetch built-in quant factor signals"],
):
    """Generate built-in quant strategy signals from predefined alpha factor formulas."""
    return generate_builtin_quant_signals(pair=pair)


if __name__ == "__main__":
    # 模拟环境配置 (测试用)
    os.environ["CURRENT_WARMUP_CANDLES"] = "200"
    
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=250, freq='D')
    
    close_prices = 100 + np.random.randn(250).cumsum()

    
    requested_indicators = ['close_50_sma', 'macd', 'rsi']
    
    try:

        df_final = calculate_indicators("WETH/USDC", requested_indicators)

        print(df_final)
    except Exception as e:
        print(f"执行拦截: {e}")