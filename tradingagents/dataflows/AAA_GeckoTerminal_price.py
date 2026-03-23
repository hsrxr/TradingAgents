import requests
import pandas as pd
import json
from .AAA_adress_mapping import AERODROME_PAIRS

def get_dex_ohlcv(pool: str, timeframe: str = "hour", limit: int = 100) -> pd.DataFrame:
    """
    获取指定流动性池的历史 OHLCV 时间序列数据。
    
    :param pool: 交易对名称，如 'WETH/USDC'
    :param timeframe: 时间级别，可选 'minute', 'hour', 'day'
    :param limit: 获取的数据条数(GeckoTerminal 免费版通常单次最高 1000)
    :return: 包含时间序列的 pandas DataFrame
    """
    # GeckoTerminal 的底层网络标识 Base 链为 'base'
    if pool not in AERODROME_PAIRS:
        raise ValueError(f"❌ 交易对 {pool} 的池地址未配置，请检查 AAA_adress_mapping.py 中的 AERODROME_PAIRS 字典")
    url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{AERODROME_PAIRS[pool]}/ohlcv/{timeframe}?token=quote&currency=token"
    
    params = {
        "limit": limit
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # with open(f"tradingagents\\dataflows\\test_data_cache\\{pool.replace('/', '_')}_ohlcv_raw.json", "w") as f:
        #     json.dump(data, f, indent=4)


        if "data" in data and "attributes" in data["data"]:
            ohlcv_list = data["data"]["attributes"]["ohlcv_list"]
            
            # GeckoTerminal 返回的格式是: [timestamp, open, high, low, close, volume]
            df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
            
            # 将 Unix 时间戳转换为人类可读的时间格式
            df["datetime"] = pd.to_datetime(df["timestamp"], unit='s')
            
            # API 默认返回是最新的在前面，量化处理时通常需要按时间正序排列（最旧在最前）
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 调整列的顺序，方便查看
            df = df[["datetime", "open", "high", "low", "close", "volume", "timestamp"]]
            
            df.to_csv(f"tradingagents\\dataflows\\data_cache\\{pool.replace('/', '_')}_ohlcv.csv", index=False)

            return df
        else:
            print("未获取到有效的 OHLCV 数据，请检查地址或网络。")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"请求 GeckoTerminal API 失败: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    PAIR = "WETH/USDC"
    
    print("正在拉取过去 100 个小时的 K 线数据...")
    df_historical = get_dex_ohlcv(PAIR, timeframe="minute", limit=100)
    
    df_historical.to_csv(f"tradingagents\\dataflows\\test_data_cache\\{PAIR.replace('/', '_')}_ohlcv.csv", index=False)
    
    if not df_historical.empty:
        print("\n成功获取时间序列数据！前 5 条记录如下：")
        print(df_historical.head())
        print("\n数据表信息：")
        print(df_historical.info())