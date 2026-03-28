import os
from dotenv import load_dotenv
import requests
from typing import Dict, Any, Optional

class LunarCrushAgentTool:
    """
    提供给 Trading Agent 的 LunarCrush 社交和新闻数据工具。
    Agent 可以通过调用这些方法来获取市场情绪信号，从而辅助交易决策。
    """
    
    BASE_URL = "https://lunarcrush.com/api4/public"

    def __init__(self, api_key: Optional[str] = None):
        # 优先使用传入的 API Key，否则从环境变量读取
        self.api_key = api_key or os.getenv("LUNARCRUSH_API_KEY")
        if not self.api_key:
            raise ValueError("Missing LunarCrush API Key. Please set the LUNARCRUSH_API_KEY environment variable.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    def get_crypto_news(self, topic: str) -> Dict[str, Any]:
        """
        [Agent Tool] 
        获取特定加密货币或主题的最新热门新闻。
        当需要分析宏观叙事、重大利好/利空事件时调用此工具。
        
        参数:
            topic (str): 需要查询的加密货币或主题标识符 (例如: 'bitcoin', 'solana', 'defi').
            
        返回:
            dict: 包含文章标题、链接、发布时间以及相关新闻参与度指标的 JSON 响应。
        """
        url = f"{self.BASE_URL}/topic/{topic}/news/v1"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch news for {topic}: {str(e)}"}

    def get_social_posts(self, topic: str) -> Dict[str, Any]:
        """
        [Agent Tool] 
        获取特定加密货币在 X (Twitter), Reddit 等平台的实时社交帖子。
        当需要判断散户情绪、KOL(创作者) 观点或捕捉早期 FOMO/FUD 信号时调用此工具。
        
        参数:
            topic (str): 需要查询的加密货币或主题标识符 (例如: 'ethereum', 'pepe').
            
        返回:
            dict: 包含帖子内容、创作者影响力和社交参与度指标的 JSON 响应。
        """
        url = f"{self.BASE_URL}/topic/{topic}/posts/v1"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch social posts for {topic}: {str(e)}"}

    def get_topic_intelligence(self, topic: str) -> Dict[str, Any]:
        """
        [Agent Tool] 
        获取加密货币的整体社交情绪与市场评分汇总（包含著名的 Galaxy Score™）。
        当需要快速评估一个币种当前整体热度、社交主导率和量价健康度时调用。
        
        参数:
            topic (str): 需要查询的加密货币或主题标识符。
            
        返回:
            dict: 包含 Galaxy Score, 社交主导率、情绪指数以及价格/交易量指标的 JSON。
        """
        url = f"{self.BASE_URL}/topic/{topic}/v1"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch topic intelligence for {topic}: {str(e)}"}


if __name__ == "__main__":
    # 简单测试
    load_dotenv()
    agent_tool = LunarCrushAgentTool(api_key="0uf6hfa3k22nnrtl5qm7wg4efolmn74f14l57cv05t")

    news = agent_tool.get_crypto_news("bitcoin")
    # social_posts = agent_tool.get_social_posts("bitcoin")
    # intelligence = agent_tool.get_topic_intelligence("bitcoin")
    
    print("News:", news)
    # print("Social Posts:", social_posts)
    # print("Topic Intelligence:", intelligence)