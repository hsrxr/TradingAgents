from typing import TYPE_CHECKING

from .default_config import DEFAULT_CONFIG

if TYPE_CHECKING:
	from .graph.trading_graph import TradingAgentsGraph
	from .triggers import AgentTriggerRuntime, TriggerEventBus, build_default_runtime

__all__ = [
	"TradingAgentsGraph",
	"DEFAULT_CONFIG",
	"AgentTriggerRuntime",
	"TriggerEventBus",
	"build_default_runtime",
]


def __getattr__(name: str):
	"""Lazily import heavy modules to avoid package import cycles."""
	if name == "TradingAgentsGraph":
		from .graph.trading_graph import TradingAgentsGraph

		return TradingAgentsGraph
	if name in {"AgentTriggerRuntime", "TriggerEventBus", "build_default_runtime"}:
		from .triggers import AgentTriggerRuntime, TriggerEventBus, build_default_runtime

		return {
			"AgentTriggerRuntime": AgentTriggerRuntime,
			"TriggerEventBus": TriggerEventBus,
			"build_default_runtime": build_default_runtime,
		}[name]
	raise AttributeError(f"module 'tradingagents' has no attribute {name!r}")
