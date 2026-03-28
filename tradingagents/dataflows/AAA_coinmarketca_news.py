import requests
import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
# 如果使用 LangChain，可以取消下一行的注释
# from langchain.tools import tool 

class CMCContentToolInput(BaseModel):
    action: str = Field(
        ..., 
        description="要执行的操作。可选值: 'trending_tokens' (获取社区热门代币), 'latest_news' (获取加密货币最新新闻)"
    )
    symbol: Optional[str] = Field(
        None, 
        description="代币符号 (例如: 'BTC', 'ETH')。仅在 action 为 'latest_news' 时有效，用于过滤特定代币的新闻。"
    )
    limit: Optional[int] = Field(
        10, 
        description="返回结果的数量限制，默认 10，最大 100。"
    )

# @tool("coinmarketcap_content_tool", args_schema=CMCContentToolInput) # LangChain 装饰器
def coinmarketcap_content_tool(action: str, symbol: Optional[str] = None, limit: int = 10) -> str:
    """
    用于为交易代理获取 CoinMarketCap 上的社区热门代币趋势和最新加密货币新闻。
    """
    # 替换为你的真实 CoinMarketCap API Key
    API_KEY = "7ebf6bdd56db4f0d9c6b98355b1aebca"
    BASE_URL = "https://pro-api.coinmarketcap.com"
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }

    try:
        if action == "trending_tokens":
            # 获取社区讨论度最高的 trending tokens
            url = f"{BASE_URL}/v1/community/trending/token"
            parameters = {
                'limit': limit
            }
            response = requests.get(url, headers=headers, params=parameters)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            # 整理返回给 Agent 的精简数据
            results = []
            for item in data:
                results.append({
                    "name": item.get('name'),
                    "symbol": item.get('symbol'),
                    "slug": item.get('slug'),
                    "price": item.get('quote', {}).get('USD', {}).get('price'),
                    "percent_change_24h": item.get('quote', {}).get('USD', {}).get('percent_change_24h')
                })
            return json.dumps({"status": "success", "trending_tokens": results}, ensure_ascii=False)

        elif action == "latest_news":
            # 获取最新新闻/文章内容
            url = f"{BASE_URL}/v1/content/latest"
            parameters = {
                'limit': limit
            }
            if symbol:
                parameters['symbol'] = symbol
                
            response = requests.get(url, headers=headers, params=parameters)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            # 整理返回给 Agent 的精简数据
            results = []
            for item in data:
                results.append({
                    "title": item.get('title'),
                    "source": item.get('source_name'),
                    "created_at": item.get('created_at'),
                    "url": item.get('meta', {}).get('sourceUrl') or item.get('url'),
                    "summary": item.get('subtitle') or item.get('title') # 如果有摘要则返回摘要
                })
            return json.dumps({"status": "success", "news": results}, ensure_ascii=False)
            
        else:
            return json.dumps({"status": "error", "message": "未知的 action 参数。请使用 'trending_tokens' 或 'latest_news'。"})

    except requests.exceptions.RequestException as e:
        return json.dumps({"status": "error", "message": f"API 调用失败: {str(e)}"})

# 测试调用示例
if __name__ == "__main__":
    # 获取热门代币
    print(coinmarketcap_content_tool(action="trending_tokens", limit=5))
    
    # 获取比特币最新新闻
    print(coinmarketcap_content_tool(action="latest_news", symbol="BTC", limit=3))
    pass