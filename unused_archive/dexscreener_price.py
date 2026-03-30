import json
import requests
from ..tradingagents.dataflows.address_mapping import get_token_address, AERODROME_PAIRS

def get_aerodrome_pool_data(pairs: str) -> dict:
    """
    Retrieve real-time price and liquidity data based on the Pair address of the liquidity pool
    """
    
    if pairs not in AERODROME_PAIRS:
        raise ValueError(f"❌ 交易对 {pairs} 的池地址未配置，请检查 address_mapping.py 中的 AERODROME_PAIRS 字典")

    pair_address = AERODROME_PAIRS[pairs]

    url = f"https://api.dexscreener.com/latest/dex/pairs/base/{pair_address}"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0" # 建议加上基础的 User-Agent 避免被防火墙拦截
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status() # 检查 HTTP 状态码
        data = response.json()

        # 校验返回数据是否为空
        if data.get("pairs"):
            
            # 将完整的data保存到tradingagents\dataflows\test_data_cache中，以便后续分析和调试
            with open(f"tradingagents\\dataflows\\test_data_cache\\aerodrome_pool_data.json", "w") as f:
                json.dump(data, f, indent=4)


            pool_data = data["pairs"][0]

            return {
                "base_token": pool_data["baseToken"]["symbol"],
                "quote_token": pool_data["quoteToken"]["symbol"],
                "price_usd": float(pool_data.get("priceUsd", 0)),
                "price_native": float(pool_data.get("priceNative", 0)), # 相对于以太坊的价格
                "liquidity_usd": float(pool_data.get("liquidity", {}).get("usd", 0)),
                "volume_24h": float(pool_data.get("volume", {}).get("h24", 0))
            }
        else:
            print("未找到该交易对数据，请检查地址或网络。")
            return None

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        return None


if __name__ == "__main__":
    market_data = get_aerodrome_pool_data("WETH/USDC")
    if market_data:
        print(market_data)
