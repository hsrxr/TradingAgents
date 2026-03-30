from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class TriggerEvent:
    """Single trigger emitted by an observer."""

    event_type: str
    pair: str
    source: str
    occurred_at: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "pair": self.pair,
            "source": self.source,
            "occurred_at": self.occurred_at.isoformat(),
            "confidence": self.confidence,
            "payload": self.payload,
        }


@dataclass
class MarketShockEvent:
    """Aggregated wake-up event produced by the event bus."""

    pair: str
    created_at: datetime
    first_event_at: datetime
    last_event_at: datetime
    trigger_events: List[TriggerEvent] = field(default_factory=list)

    def to_context(self) -> Dict[str, Any]:
        return {
            "market_shock": {
                "pair": self.pair,
                "created_at": self.created_at.isoformat(),
                "first_event_at": self.first_event_at.isoformat(),
                "last_event_at": self.last_event_at.isoformat(),
                "event_count": len(self.trigger_events),
                "events": [event.as_dict() for event in self.trigger_events],
            }
        }

    def summary_text(self) -> str:
        event_types = ", ".join(sorted({e.event_type for e in self.trigger_events}))
        return (
            f"Market_Shock for {self.pair}: {len(self.trigger_events)} event(s), "
            f"types=[{event_types}], window={self.first_event_at.isoformat()} -> {self.last_event_at.isoformat()}"
        )
