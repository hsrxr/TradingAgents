import logging

from dotenv import load_dotenv
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.triggers.runtime import build_default_runtime


logging.basicConfig(level=logging.INFO)
load_dotenv()

def main() -> None:
    config = DEFAULT_CONFIG.copy()

    graph = TradingAgentsGraph(
        debug=True,
        selected_analysts=["market", "news", "quant"],
        config=config,
        parallel_mode=True,
    )

    runtime = build_default_runtime(
        graph=graph,
        pairs=config.get("trigger_pairs", ["WETH/USDC"]),
        source_allowlist=config.get("trigger_news_sources", ["sec", "twitter", "project"]),
        twitter_handles=config.get("trigger_twitter_accounts", []),
        nitter_instances=config.get("trigger_nitter_instances", []),
        aggregation_window_seconds=config.get("trigger_aggregation_window_seconds", 90),
        cooldown_seconds=config.get("trigger_cooldown_seconds", 300),
        poll_interval_seconds=config.get("trigger_poll_interval_seconds", 10),
    )

    runtime.run_forever()


if __name__ == "__main__":
    main()
