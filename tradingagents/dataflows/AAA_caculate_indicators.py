import os
import json
import pandas as pd
import numpy as np

from typing import List, Union, Callable, Dict

def load_price_data(pair: str) -> pd.DataFrame:
    DATA_CACHE_DIR = os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")
    file_path = f"{DATA_CACHE_DIR}/prices/{pair.replace('/', '_')}_ohlcv.csv"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data cache not found: {file_path}")
    print(pd.read_csv(file_path, parse_dates=['datetime']).head())
    return pd.read_csv(file_path, parse_dates=['datetime'])


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

def calculate_indicators(pair: str, indicators: Union[str, List[str]] = None) -> pd.DataFrame:
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

    # 4. 全量计算指标
    results = {ind: INDICATOR_REGISTRY[ind](df) for ind in indicators}
    result_df = pd.DataFrame(results, index=df.index)

    # 5. 从 meta 文件读取 warmup，并截断预热 K 线 (Warmup Truncation)
    warmup_len = load_warmup_len_from_meta(pair)
    
    if warmup_len > 0:
        # 防溢出：确保截断长度不会超过数据总长度
        safe_cut = min(warmup_len, len(result_df))
        result_df = result_df.iloc[safe_cut:].copy()

    # 6. 添加 datetime 列到返回结果
    result_df['datetime'] = df.loc[result_df.index, 'datetime'].values

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
    return np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))

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