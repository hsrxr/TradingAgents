import json
import re
from typing import Any, Dict


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_action_and_confidence(trader_plan: str) -> Dict[str, Any]:
    """Extract action and confidence from Chief Trader JSON/text output."""
    action = "HOLD"
    confidence = 0.5

    # Try JSON parse first.
    try:
        obj = json.loads(trader_plan)
        candidate_action = str(obj.get("action", "HOLD")).upper()
        if candidate_action in {"BUY", "SELL", "HOLD"}:
            action = candidate_action
        confidence = _safe_float(obj.get("confidence", 0.5), 0.5)
        return {"action": action, "confidence": max(0.0, min(1.0, confidence))}
    except Exception:
        pass

    # Fallback text heuristics.
    upper_text = trader_plan.upper()
    if "SELL" in upper_text:
        action = "SELL"
    elif "BUY" in upper_text:
        action = "BUY"

    match = re.search(r"(0(?:\.\d+)?|1(?:\.0+)?)", trader_plan)
    if match:
        confidence = _safe_float(match.group(1), 0.5)

    return {"action": action, "confidence": max(0.0, min(1.0, confidence))}


def create_risk_engine():
    """Pure Python risk engine and position sizer (no LLM)."""

    def risk_engine_node(state) -> Dict[str, Any]:
        trader_plan = state.get("trader_investment_plan", "")
        parsed = _extract_action_and_confidence(trader_plan)

        action = parsed["action"]
        confidence = parsed["confidence"]

        portfolio = state.get("portfolio_balance", {}) or {}
        cash_usd = _safe_float(portfolio.get("cash_usd", 10000.0), 10000.0)
        position_usd = _safe_float(portfolio.get("position_usd", 0.0), 0.0)

        max_position_pct = 0.20
        max_single_order_pct = 0.10
        confidence_floor = 0.35

        capped_confidence = max(confidence_floor, confidence)
        target_gross_limit = cash_usd * max_position_pct
        max_order_notional = cash_usd * max_single_order_pct

        if action == "HOLD":
            order_notional = 0.0
            risk_status = "blocked: hold"
        elif action == "BUY":
            available_for_buy = max(0.0, target_gross_limit - position_usd)
            order_notional = min(max_order_notional, available_for_buy) * capped_confidence
            risk_status = "allowed" if order_notional > 0 else "blocked: position_limit"
        else:  # SELL
            order_notional = min(max_order_notional, position_usd if position_usd > 0 else max_order_notional) * capped_confidence
            risk_status = "allowed" if order_notional > 0 else "blocked: no_position"

        order = {
            "ticker": state.get("company_of_interest", ""),
            "side": action,
            "order_type": "market",
            "notional_usd": round(order_notional, 2),
            "quantity": None,
            "confidence": round(confidence, 3),
            "risk_status": risk_status,
            "max_position_pct": max_position_pct,
            "max_single_order_pct": max_single_order_pct,
        }

        final_decision = {
            "action": action,
            "confidence": round(confidence, 3),
            "order": order,
            "reason": "Risk engine applied deterministic position and exposure limits.",
        }

        risk_debate_state = state.get("risk_debate_state", {}) or {}
        updated_risk_state = {
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "history": risk_debate_state.get("history", ""),
            "latest_speaker": "Risk Engine",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "judge_decision": json.dumps(final_decision, ensure_ascii=False),
            "count": risk_debate_state.get("count", 0),
        }

        return {
            "risk_debate_state": updated_risk_state,
            "final_trade_decision": json.dumps(final_decision, ensure_ascii=False),
        }

    return risk_engine_node
