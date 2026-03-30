from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .models import MarketShockEvent, TriggerEvent


@dataclass
class _AggregationBucket:
    pair: str
    first_event_at: datetime
    last_event_at: datetime
    events: List[TriggerEvent] = field(default_factory=list)


class TriggerEventBus:
    """Aggregates bursty triggers into a single Market_Shock wake-up."""

    def __init__(
        self,
        aggregation_window_seconds: int = 90,
        cooldown_seconds: int = 300,
        max_events_per_pair: int = 200,
    ) -> None:
        self.aggregation_window = timedelta(seconds=max(1, aggregation_window_seconds))
        self.cooldown = timedelta(seconds=max(0, cooldown_seconds))
        self.max_events_per_pair = max(1, max_events_per_pair)
        self._buckets: Dict[str, _AggregationBucket] = {}
        self._last_emitted_at: Dict[str, datetime] = {}

    def publish(self, event: TriggerEvent) -> None:
        bucket = self._buckets.get(event.pair)
        if bucket is None:
            self._buckets[event.pair] = _AggregationBucket(
                pair=event.pair,
                first_event_at=event.occurred_at,
                last_event_at=event.occurred_at,
                events=[event],
            )
            return

        bucket.last_event_at = max(bucket.last_event_at, event.occurred_at)
        bucket.events.append(event)
        if len(bucket.events) > self.max_events_per_pair:
            bucket.events = bucket.events[-self.max_events_per_pair :]

    def pop_ready_market_shocks(self, now: datetime | None = None) -> List[MarketShockEvent]:
        now = now or datetime.now(timezone.utc)
        ready_pairs: List[str] = []

        for pair, bucket in self._buckets.items():
            quiet_long_enough = (now - bucket.last_event_at) >= self.aggregation_window
            if not quiet_long_enough:
                continue

            last_emit_at = self._last_emitted_at.get(pair)
            cooled_down = last_emit_at is None or (now - last_emit_at) >= self.cooldown
            if cooled_down:
                ready_pairs.append(pair)

        market_shocks: List[MarketShockEvent] = []
        for pair in ready_pairs:
            bucket = self._buckets.pop(pair)
            market_shocks.append(
                MarketShockEvent(
                    pair=pair,
                    created_at=now,
                    first_event_at=bucket.first_event_at,
                    last_event_at=bucket.last_event_at,
                    trigger_events=bucket.events,
                )
            )
            self._last_emitted_at[pair] = now

        return market_shocks

    def pending_pairs(self) -> List[str]:
        return list(self._buckets.keys())
