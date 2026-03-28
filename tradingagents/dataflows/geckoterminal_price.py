import requests
import pandas as pd
import json
import os
import datetime
from typing import Annotated
from langchain_core.tools import tool
from tradingagents.dataflows.address_mapping import AERODROME_PAIRS


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
        dt_obj = pd.to_datetime(tradedate)
        before_timestamp = int(dt_obj.timestamp())
    except Exception as e:
        raise ValueError(f"❌ 解析 tradedate 失败，请检查时间格式: {e}")

    # --- 1. 动态计算并确定实际的 WARMUP_CANDLES ---
    IDEAL_WARMUP = 200 
    
    # GeckoTerminal 单次最大限制 1000
    if limit + IDEAL_WARMUP > 1000:
        actual_warmup = 1000 - limit
        if actual_warmup < 0:
            actual_warmup = 0
            limit = 1000 # 如果 Agent 本身就请求超过 1000，强制截断
        print(f"⚠️ 警告: 请求总数据量超限，预热 K 线数已被动态压缩为 {actual_warmup} 根。")
    else:
        actual_warmup = IDEAL_WARMUP
        
    total_limit = limit + actual_warmup

    url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{AERODROME_PAIRS[pair]}/ohlcv/{timeframe}"
    
    params = {
        "limit": total_limit,
        "before_timestamp": before_timestamp,
        "token": "quote",     
        "currency": "token"   
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "data" in data and "attributes" in data["data"]:
            ohlcv_list = data["data"]["attributes"]["ohlcv_list"]
            
            df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit='s')
            df = df[["datetime", "open", "high", "low", "close", "volume", "timestamp"]]
            
            # 转换为量化标准：按时间正序排列
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            DATA_CACHE_DIR = os.getenv("DATA_CACHE_DIR", "tradingagents/dataflows/data_cache")
            os.makedirs(DATA_CACHE_DIR, exist_ok=True) 
            
            # 保存全量 K 线数据 (预热 + Agent 请求)
            csv_path = os.path.join(f"{DATA_CACHE_DIR}/prices", f"{pair.replace('/', '_')}_ohlcv.csv")
            df.to_csv(csv_path, index=False)

            total_fetched = len(df)      
            actual_warmup = min(actual_warmup, total_fetched - limit) if total_fetched > limit else 0      

            meta_path = os.path.join(DATA_CACHE_DIR, f"{pair.replace('/', '_')}_meta.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "actual_warmup": actual_warmup, 
                    "agent_limit": limit,
                    "total_fetched": len(df)
                }, f, ensure_ascii=False, indent=4)
            

            df_agent = df.tail(limit).reset_index(drop=True)
            return df_agent
            
        else:
            print("未获取到有效的 OHLCV 数据，请检查地址或网络。")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"请求 GeckoTerminal API 失败: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    PAIR = "WETH/USDC"
    
    # 模拟 Agent 在过去的某个时刻请求数据
    TRADEDATE = "2026-03-01 12:00:00" 
    AGENT_LIMIT = 100
    
    print(f"正在拉取 {TRADEDATE} 之前的数据 (Agent 需 {AGENT_LIMIT} 根，系统额外拉取预热数据)...")
    
    df_agent_data = get_dex_ohlcv(PAIR, tradedate=TRADEDATE, timeframe="day", limit=AGENT_LIMIT)
    
    if not df_agent_data.empty:
        print(f"\n✅ 成功获取！只给 Agent 返回了请求的 {len(df_agent_data)} 条记录。")
        print("\nAgent 看到的最后 5 条记录（确保没有超过 TRADEDATE）：")
        print(df_agent_data.tail())