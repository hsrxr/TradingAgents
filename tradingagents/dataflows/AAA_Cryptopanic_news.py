import requests
from typing import List, Dict, Optional
from datetime import datetime

class CryptoPanicNewsTool:
    """
    为 Trading Agent 提供 CryptoPanic 加密货币新闻的工具类。
    """
    BASE_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, api_token: str):
        """
        初始化工具
        :param api_token: 你的 CryptoPanic API Token
        """
        self.api_token = api_token

    def get_news(
        self,
        currencies: Optional[str] = None,
        filter_type: Optional[str] = None,
        kind: str = "news",
        regions: str = "en",
        limit: int = 10
    ) -> List[Dict]:
        """
        获取加密货币新闻。
        
        :param currencies: 货币代码，多个用逗号分隔 (例如: "BTC,ETH")
        :param filter_type: 新闻过滤器 (可选: "rising", "hot", "bullish", "bearish", "important")
        :param kind: 类型 (可选: "news", "media", "all")
        :param regions: 语言区域 (默认: "en" 英语)
        :param limit: 提取的新闻条数限制 (默认 10)
        :return: 包含新闻关键信息的字典列表，适合 Agent 直接读取分析
        """
        params = {
            "auth_token": self.api_token,
            "kind": kind,
            "regions": regions
        }

        if currencies:
            params["currencies"] = currencies
        if filter_type:
            # 确保传入的 filter_type 是 API 支持的
            valid_filters = ["rising", "hot", "bullish", "bearish", "important", "saved", "lol"]
            if filter_type in valid_filters:
                params["filter"] = filter_type
            else:
                raise ValueError(f"Invalid filter_type. Must be one of {valid_filters}")

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 解析并提取对 Agent 有用的字段
            results = data.get("results", [])
            agent_news_feed = []
            
            for item in results[:limit]:
                # 提取情绪投票数据
                votes = item.get("votes", {})
                bullish_votes = votes.get("bullish", 0)
                bearish_votes = votes.get("bearish", 0)
                important_votes = votes.get("important", 0)
                
                # 提取涉及的代币
                mentioned_coins = [coin.get("code") for coin in item.get("currencies", [])] if item.get("currencies") else []

                news_data = {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "published_at": item.get("created_at"),
                    "source_domain": item.get("domain"),
                    "url": item.get("url"),
                    "mentioned_coins": mentioned_coins,
                    "sentiment_votes": {
                        "bullish": bullish_votes,
                        "bearish": bearish_votes,
                        "important": important_votes,
                        # 简单的情绪得分计算 (看涨 - 看跌)
                        "net_score": bullish_votes - bearish_votes
                    }
                }
                agent_news_feed.append(news_data)
                
            return agent_news_feed

        except requests.exceptions.RequestException as e:
            print(f"Error fetching news from CryptoPanic: {e}")
            return []

# ==========================================
# 使用示例 (测试时请替换为你的真实 API Token)
# ==========================================
if __name__ == "__main__":
    # 替换为你在 https://cryptopanic.com/developers/api/ 获取的 Token
    API_TOKEN = "a6775b2166ec6acfc08e1003004e1fc5efc92f48" 
    
    news_tool = CryptoPanicNewsTool(api_token=API_TOKEN)
    
    # 场景 1：获取关于 BTC 和 ETH 的重要新闻
    print("--- Fetching Important BTC/ETH News ---")
    btc_eth_news = news_tool.get_news(currencies="BTC,ETH", filter_type="important", limit=3)
    for news in btc_eth_news:
        print(f"[{news['published_at']}] {news['title']}")
        print(f"Coins: {news['mentioned_coins']} | Sentiment Score: {news['sentiment_votes']['net_score']} (Bullish: {news['sentiment_votes']['bullish']}, Bearish: {news['sentiment_votes']['bearish']})\n")