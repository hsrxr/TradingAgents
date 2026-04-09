"""
Record trade outcomes and approval/rejection feedback in agent memory.

This module extends the reflection system to capture actual trade results
from RiskRouter and store them in agent memory for learning.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from tradingagents.agents.utils.memory import FinancialSituationMemory

logger = logging.getLogger(__name__)


class TradeOutcomeRecorder:
    """Record actual trade outcomes in agent memory for learning."""
    
    def __init__(self):
        """Initialize the trade outcome recorder."""
        self.trades_recorded = 0
    
    def record_approved_trade(
        self,
        memory: FinancialSituationMemory,
        decision_state: Dict[str, Any],
        approval_event: Dict[str, Any],
        portfolio_outcome: Optional[Dict[str, Any]] = None,
        trade_date: str = None,
    ) -> bool:
        """Record an approved and executed trade in memory.
        
        Args:
            memory: Target FinancialSituationMemory instance
            decision_state: The final decision state from analysis
            approval_event: TradeApprovalEvent dict
            portfolio_outcome: Portfolio changes from execution
            trade_date: Date of trade
        
        Returns:
            True if successfully recorded
        """
        try:
            decision = json.loads(decision_state.get("final_trade_decision", "{}"))
            order = decision.get("order", {})
            
            # Build memory situation
            situation = {
                "action": decision.get("action", "HOLD").upper(),
                "ticker": order.get("ticker", "UNKNOWN"),
                "confidence": decision.get("confidence", 0.5),
                "notional_usd": order.get("notional_usd", 0),
                "approval_status": "approved",
                "pnl_result": "pending",  # Will be updated after execution
                "pnl_value": 0.0,
                "reasoning": decision.get("reason", ""),
                "timestamp": trade_date or datetime.now().isoformat(),
                "on_chain_hash": approval_event.get("transaction_hash", ""),
                "intent_hash": approval_event.get("intent_hash", ""),
                "portfolio_impact": portfolio_outcome or {},
            }
            
            # Add to memory with metadata
            metadata = {
                "approval_status": "approved",
                "trade_date": trade_date or datetime.now().isoformat(),
                "on_chain": True,
            }
            
            memory.add_situations(
                [f"Trade {situation['action']} {situation['ticker']} approved for {situation['notional_usd']} USD"],
                metadata=metadata,
            )
            
            self.trades_recorded += 1
            logger.info(
                f"Recorded approved trade in memory: {situation['action']} "
                f"{situation['ticker']} @ confidence {situation['confidence']:.1%}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error recording approved trade: {e}", exc_info=True)
            return False
    
    def record_rejected_trade(
        self,
        memory: FinancialSituationMemory,
        decision_state: Dict[str, Any],
        rejection_event: Dict[str, Any],
        rejection_reason: str,
        trade_date: str = None,
    ) -> bool:
        """Record a rejected trade in memory.
        
        Args:
            memory: Target FinancialSituationMemory instance
            decision_state: The final decision state from analysis
            rejection_event: TradeRejectionEvent dict
            rejection_reason: Reason for rejection from RiskRouter
            trade_date: Date of trade
        
        Returns:
            True if successfully recorded
        """
        try:
            decision = json.loads(decision_state.get("final_trade_decision", "{}"))
            order = decision.get("order", {})
            
            # Build memory situation
            situation = {
                "action": decision.get("action", "HOLD").upper(),
                "ticker": order.get("ticker", "UNKNOWN"),
                "confidence": decision.get("confidence", 0.5),
                "notional_usd": order.get("notional_usd", 0),
                "approval_status": "rejected",
                "rejection_reason": rejection_reason,
                "reasoning": decision.get("reason", ""),
                "timestamp": trade_date or datetime.now().isoformat(),
                "on_chain_hash": rejection_event.get("transaction_hash", ""),
                "intent_hash": rejection_event.get("intent_hash", ""),
            }
            
            # Add to memory with metadata
            metadata = {
                "approval_status": "rejected",
                "rejection_reason": rejection_reason,
                "trade_date": trade_date or datetime.now().isoformat(),
                "on_chain": True,
            }
            
            memory.add_situations(
                [f"Trade {situation['action']} {situation['ticker']} REJECTED: {rejection_reason}"],
                metadata=metadata,
            )
            
            self.trades_recorded += 1
            logger.info(
                f"Recorded rejected trade in memory: {situation['action']} "
                f"{situation['ticker']} - Reason: {rejection_reason}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error recording rejected trade: {e}", exc_info=True)
            return False
    
    def record_trade_outcome_for_all_agents(
        self,
        agent_memories: Dict[str, FinancialSituationMemory],
        decision_state: Dict[str, Any],
        approval_status: str,
        trade_date: str = None,
        approval_event: Optional[Dict[str, Any]] = None,
        rejection_event: Optional[Dict[str, Any]] = None,
        rejection_reason: Optional[str] = None,
        portfolio_outcome: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """Record trade outcome in all agent memories.
        
        Args:
            agent_memories: Dict of agent_name -> FinancialSituationMemory
            decision_state: Final decision state
            approval_status: "approved" or "rejected"
            trade_date: Date of trade
            approval_event: TradeApprovalEvent dict (if approved)
            rejection_event: TradeRejectionEvent dict (if rejected)
            rejection_reason: Rejection reason (if rejected)
            portfolio_outcome: Portfolio changes (if approved)
        
        Returns:
            Dict of agent_name -> success_boolean
        """
        results = {}
        
        for agent_name, memory in agent_memories.items():
            if approval_status == "approved":
                success = self.record_approved_trade(
                    memory=memory,
                    decision_state=decision_state,
                    approval_event=approval_event,
                    portfolio_outcome=portfolio_outcome,
                    trade_date=trade_date,
                )
            elif approval_status == "rejected":
                success = self.record_rejected_trade(
                    memory=memory,
                    decision_state=decision_state,
                    rejection_event=rejection_event,
                    rejection_reason=rejection_reason,
                    trade_date=trade_date,
                )
            else:
                logger.warning(f"Unknown approval status: {approval_status}")
                success = False
            
            results[agent_name] = success
        
        logger.info(
            f"Recorded trade outcome in {sum(results.values())}/{len(results)} agent memories"
        )
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about recorded trades.
        
        Returns:
            Dict with trade recording stats
        """
        return {
            "total_trades_recorded": self.trades_recorded,
        }


def create_trade_outcome_recorder() -> TradeOutcomeRecorder:
    """Factory function to create a TradeOutcomeRecorder.
    
    Returns:
        TradeOutcomeRecorder instance
    """
    return TradeOutcomeRecorder()
