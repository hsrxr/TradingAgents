from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from tradingagents.graph.trading_graph import TradingAgentsGraph

from .event_bus import TriggerEventBus
from .models import MarketShockEvent, TriggerEvent
from .observers import (
    BaseTriggerObserver,
    HourlyBoundaryObserver,
    NewsSource,
    PollingNewsObserver,
    PriceActionObserver,
    SecPressReleaseSource,
    TwitterAccountsRssSource,
)


logger = logging.getLogger(__name__)


class AgentTriggerRuntime:
    """Lightweight observer/event-bus scheduler outside LangGraph."""

    def __init__(
        self,
        graph: "TradingAgentsGraph",
        pairs: List[str],
        observers: List[BaseTriggerObserver],
        event_bus: Optional[TriggerEventBus] = None,
        poll_interval_seconds: int = 10,
        on_decision: Optional[Callable[[MarketShockEvent, Dict[str, Any], str], None]] = None,
    ) -> None:
        self.graph = graph
        self.pairs = pairs
        self.observers = observers
        self.event_bus = event_bus or TriggerEventBus()
        self.poll_interval_seconds = max(1, poll_interval_seconds)
        self.on_decision = on_decision

    def run_once(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now(timezone.utc)

        emitted_events = self._poll_observers(now)
        for event in emitted_events:
            self.event_bus.publish(event)

        wakeups: List[Dict[str, Any]] = []
        for market_shock in self.event_bus.pop_ready_market_shocks(now=now):
            wakeups.append(self._wake_agent(market_shock, now))

        return wakeups

    def run_forever(self) -> None:
        while True:
            cycle_now = datetime.now(timezone.utc)
            try:
                self.run_once(now=cycle_now)
            except Exception as exc:
                logger.exception("Trigger runtime cycle failed: %s", exc)
            time.sleep(self.poll_interval_seconds)

    def _poll_observers(self, now: datetime) -> List[TriggerEvent]:
        all_events: List[TriggerEvent] = []
        for observer in self.observers:
            try:
                events = observer.poll(now=now, pairs=self.pairs)
            except Exception as exc:
                logger.warning("Observer %s failed: %s", observer.__class__.__name__, exc)
                continue
            all_events.extend(events)
        return all_events

    def _wake_agent(self, market_shock: MarketShockEvent, now: datetime) -> Dict[str, Any]:
        trade_date = now.strftime("%Y-%m-%d %H:%M:%S")
        trigger_context = market_shock.to_context()

        logger.info("Waking agent: %s", market_shock.summary_text())
        final_state, decision = self.graph.propagate(
            market_shock.pair,
            trade_date,
            trigger_context=trigger_context,
        )

        result = {
            "pair": market_shock.pair,
            "trade_date": trade_date,
            "decision": decision,
            "event_count": len(market_shock.trigger_events),
            "event_types": sorted({e.event_type for e in market_shock.trigger_events}),
            "final_state": final_state,
        }
        if self.on_decision:
            self.on_decision(market_shock, final_state, decision)
        return result


def build_default_runtime(
    graph: "TradingAgentsGraph",
    pairs: List[str],
    pair_keywords: Optional[Dict[str, List[str]]] = None,
    source_allowlist: Optional[List[str]] = None,
    twitter_handles: Optional[List[str]] = None,
    nitter_instances: Optional[List[str]] = None,
    aggregation_window_seconds: int = 90,
    cooldown_seconds: int = 300,
    poll_interval_seconds: int = 10,
) -> AgentTriggerRuntime:
    """Factory for a default runtime with schedule/news/price observers."""

    news_sources: List[NewsSource] = [SecPressReleaseSource()]
    if twitter_handles:
        news_sources.append(
            TwitterAccountsRssSource(
                handles=twitter_handles,
                nitter_instances=nitter_instances,
            )
        )

    observers = [
        HourlyBoundaryObserver(),
        PollingNewsObserver(
            sources=news_sources,
            pair_keywords=pair_keywords,
            source_allowlist=source_allowlist or ["sec", "twitter", "project"],
        ),
        PriceActionObserver(),
    ]

    event_bus = TriggerEventBus(
        aggregation_window_seconds=aggregation_window_seconds,
        cooldown_seconds=cooldown_seconds,
    )

    return AgentTriggerRuntime(
        graph=graph,
        pairs=pairs,
        observers=cast(List[BaseTriggerObserver], observers),
        event_bus=event_bus,
        poll_interval_seconds=poll_interval_seconds,
    )
