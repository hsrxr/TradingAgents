from .event_bus import TriggerEventBus
from .models import TriggerEvent, MarketShockEvent
from .observers import (
    BaseTriggerObserver,
    HourlyBoundaryObserver,
    PollingNewsObserver,
    PriceActionObserver,
    SecPressReleaseSource,
    TwitterAccountsRssSource,
)

__all__ = [
    "TriggerEventBus",
    "TriggerEvent",
    "MarketShockEvent",
    "BaseTriggerObserver",
    "HourlyBoundaryObserver",
    "PollingNewsObserver",
    "PriceActionObserver",
    "SecPressReleaseSource",
    "TwitterAccountsRssSource",
    "AgentTriggerRuntime",
    "build_default_runtime",
]


def __getattr__(name: str):
    """Lazy-load runtime helpers to avoid circular imports during graph bootstrap."""
    if name in {"AgentTriggerRuntime", "build_default_runtime"}:
        from .runtime import AgentTriggerRuntime, build_default_runtime

        return {
            "AgentTriggerRuntime": AgentTriggerRuntime,
            "build_default_runtime": build_default_runtime,
        }[name]
    raise AttributeError(f"module 'tradingagents.triggers' has no attribute {name!r}")
