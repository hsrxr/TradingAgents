import json
from typing import Any, Dict
from tradingagents.portfolio_manager import PortfolioManager


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _strip_code_fence(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if not lines:
        return stripped

    # Remove opening fence like ```json / ```
    if lines[0].lstrip().startswith("```"):
        lines = lines[1:]

    # Remove trailing closing fence if present
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _extract_json_candidate(text: str) -> str:
    candidate = _strip_code_fence(text)
    if not candidate:
        return candidate

    # If extra prose exists, try slicing the outermost JSON object body.
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last != -1 and first < last:
        return candidate[first : last + 1].strip()

    return candidate


def _extract_action_and_confidence(trader_plan: str) -> Dict[str, Any]:
    """Extract action and confidence from Chief Trader JSON/text output."""
    action = "HOLD"
    confidence = 0.5

    # Strict JSON parse after sanitizing markdown code fences.
    try:
        obj = json.loads(_extract_json_candidate(trader_plan))
        candidate_action = str(obj.get("action", "HOLD")).upper()
        if candidate_action in {"BUY", "SELL", "HOLD"}:
            action = candidate_action
        confidence = _safe_float(obj.get("confidence", 0.5), 0.5)
        return {"action": action, "confidence": max(0.0, min(1.0, confidence))}
    except Exception:
        pass

    # Fallback text heuristics (no regex confidence extraction to avoid accidental numeric capture).
    upper_text = trader_plan.upper()
    if "SELL" in upper_text:
        action = "SELL"
    elif "BUY" in upper_text:
        action = "BUY"

    return {"action": action, "confidence": max(0.0, min(1.0, confidence))}


def create_risk_engine():
    """Pure Python risk engine and position sizer with portfolio persistence.
    
    Reads financial state directly from persistent database.
    Applies all hard rules (position limits, drawdown limits, kelly formula sizing).
    Persists updated portfolio state after order execution.
    """
    
    # Initialize portfolio manager for reading/writing persistent state
    portfolio_manager = PortfolioManager(db_path="./trade_memory/portfolio.db")

    def risk_engine_node(state) -> Dict[str, Any]:
        trader_plan = state.get("trader_investment_plan", "")
        parsed = _extract_action_and_confidence(trader_plan)

        action = parsed["action"]
        confidence = parsed["confidence"]

        # Read portfolio directly from persistent database (single source of truth)
        current_portfolio = portfolio_manager.load_latest_portfolio()
        cash_usd = _safe_float(current_portfolio.get("cash_usd", 10000.0), 10000.0)
        position_usd = _safe_float(current_portfolio.get("position_usd", 0.0), 0.0)
        unrealized_pnl = _safe_float(current_portfolio.get("unrealized_pnl", 0.0), 0.0)
        realized_pnl = _safe_float(current_portfolio.get("realized_pnl", 0.0), 0.0)

        # Risk management parameters
        max_position_pct = 0.20
        max_single_order_pct = 0.10
        confidence_floor = 0.35
        max_drawdown_pct = 0.05  # Stop loss at 5% drawdown

        capped_confidence = max(confidence_floor, confidence)
        target_gross_limit = cash_usd * max_position_pct
        max_order_notional = cash_usd * max_single_order_pct

        # Kelly formula position sizing: f = (bp - q) / b
        # Where b=odds, p=win_probability, q=loss_probability
        # Simplified: kelly_fraction = confidence - (1 - confidence) = 2*confidence - 1
        kelly_fraction = max(0.0, 2 * capped_confidence - 1)
        kelly_adjusted_notional = max_order_notional * kelly_fraction

        if action == "HOLD":
            order_notional = 0.0
            risk_status = "blocked: hold"
        elif action == "BUY":
            # Check drawdown limit before allowing new positions
            initial_capital = 10000.0
            total_assets = cash_usd + position_usd + unrealized_pnl
            drawdown = (total_assets - initial_capital) / initial_capital if initial_capital > 0 else 0
            
            if drawdown < -max_drawdown_pct:
                order_notional = 0.0
                risk_status = f"blocked: drawdown_exceeded ({drawdown*100:.2f}% vs limit {-max_drawdown_pct*100:.2f}%)"
            else:
                available_for_buy = max(0.0, target_gross_limit - position_usd)
                order_notional = min(kelly_adjusted_notional, available_for_buy)
                risk_status = "allowed" if order_notional > 0 else "blocked: position_limit"
        else:  # SELL
            # Always allow sells for risk management
            order_notional = min(kelly_adjusted_notional, position_usd if position_usd > 0 else max_order_notional)
            risk_status = "allowed" if order_notional > 0 else "blocked: no_position"

        order = {
            "ticker": state.get("company_of_interest", ""),
            "side": action,
            "order_type": "market",
            "notional_usd": round(order_notional, 2),
            "quantity": None,
            "confidence": round(confidence, 3),
            "kelly_fraction": round(kelly_fraction, 3),
            "risk_status": risk_status,
            "max_position_pct": max_position_pct,
            "max_single_order_pct": max_single_order_pct,
        }

        final_decision = {
            "action": action,
            "confidence": round(confidence, 3),
            "order": order,
            "reason": "Risk engine applied Kelly-adjusted position sizing with drawdown protection.",
        }

        # Persist portfolio state update after order processing
        # (In production, this would reflect actual trade execution)
        updated_portfolio = {
            "cash_usd": cash_usd,
            "positions": current_portfolio.get("positions", {}),
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "timestamp": state.get("trade_date"),
        }
        
        try:
            portfolio_manager.save_portfolio_state(updated_portfolio)
            if order.get("notional_usd", 0) > 0:
                portfolio_manager.record_trade(
                    ticker=order["ticker"],
                    side=order["side"],
                    quantity=0,  # Would be filled by execution engine
                    entry_price=0,  # Would be filled by execution engine
                    notional_usd=order["notional_usd"],
                )
        except Exception as e:
            # Log but don't fail the decision if persistence fails
            import logging
            logging.error(f"Failed to persist portfolio state: {e}")

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
