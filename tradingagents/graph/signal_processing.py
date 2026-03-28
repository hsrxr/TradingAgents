# TradingAgents/graph/signal_processing.py

import json
from langchain_openai import ChatOpenAI


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text

        Returns:
            Extracted decision (BUY, SELL, or HOLD)
        """
        try:
            obj = json.loads(full_signal)
            action = str(obj.get("action", "HOLD")).upper()
            if action in {"BUY", "SELL", "HOLD"}:
                return action
        except Exception:
            pass

        upper_text = full_signal.upper()
        if "SELL" in upper_text:
            return "SELL"
        if "BUY" in upper_text:
            return "BUY"
        return "HOLD"
