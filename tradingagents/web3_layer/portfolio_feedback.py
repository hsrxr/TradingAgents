"""
Apply on-chain trade approvals/rejections to portfolio state and memory.

This module provides functionality to:
1. Apply approved trades to portfolio (update positions, cash, PnL)
2. Record rejected trades and revert reserved capital
3. Store trade outcomes in agent memory for learning
4. Maintain trade history with on-chain feedback
"""

import logging
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from tradingagents.portfolio_manager import PortfolioManager
from tradingagents.web3_layer.trade_status_checker import (
    TradeApprovalEvent,
    TradeRejectionEvent,
    TradeStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class TradeExecutionOutcome:
    """Result of applying a trade to portfolio."""
    success: bool
    message: str
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    pnl_impact: float = 0.0


class PortfolioFeedbackEngine:
    """Apply on-chain trade outcomes to portfolio state and memory."""
    
    def __init__(self, portfolio_manager: PortfolioManager):
        """Initialize with portfolio manager.
        
        Args:
            portfolio_manager: PortfolioManager instance for state updates
        """
        self.portfolio_manager = portfolio_manager
        self.db_path = portfolio_manager.db_path
    
    def apply_approved_trade(
        self,
        approval_event: TradeApprovalEvent,
        trade_intent: Dict[str, Any],
        execution_price_usd: Optional[float] = None,
        execution_amount_filled: Optional[float] = None,
    ) -> TradeExecutionOutcome:
        """Apply an approved trade to portfolio.
        
        Updates:
        - positions: Add/remove or adjust asset holdings
        - cash_usd: Deduct from available cash
        - trade_history: Record the executed trade
        
        Args:
            approval_event: TradeApprovalEvent from RiskRouter
            trade_intent: Original TradeIntent dict
            execution_price_usd: Actual execution price (optional)
            execution_amount_filled: Amount actually filled (optional)
        
        Returns:
            TradeExecutionOutcome with success status and updated portfolio state
        """
        try:
            # Save current state for comparison
            current = self.portfolio_manager.load_latest_portfolio()
            previous_state = {
                "cash_usd": current.get("cash_usd", 0),
                "positions": json.loads(current.get("positions", "{}")),
                "total_assets": current.get("total_assets", 0),
            }
            
            action = str(trade_intent.get("action", "")).upper()
            pair = str(trade_intent.get("pair", "UNKNOWN"))
            amount_usd = float(approval_event.amount_usd_scaled) / 100.0
            
            # Parse positions
            positions = json.loads(
                self.portfolio_manager.get_latest_positions() or "{}"
            )
            
            # Get execution details
            price_usd = execution_price_usd or (amount_usd / 100.0)  # Fallback
            amount_filled = execution_amount_filled or amount_usd
            
            # Update positions based on action
            if action == "BUY":
                # Calculate asset amount
                asset_symbol = pair.split("/")[0] if "/" in pair else pair
                asset_amount = amount_filled / price_usd
                
                # Add to position
                if asset_symbol in positions:
                    positions[asset_symbol]["quantity"] += asset_amount
                    positions[asset_symbol]["avg_entry_price"] = (
                        (positions[asset_symbol]["avg_entry_price"] * 
                         (positions[asset_symbol]["quantity"] - asset_amount) +
                         price_usd * asset_amount) / 
                        positions[asset_symbol]["quantity"]
                    )
                else:
                    positions[asset_symbol] = {
                        "quantity": asset_amount,
                        "avg_entry_price": price_usd,
                        "entry_time": datetime.now().isoformat(),
                    }
                
                # Deduct from cash
                cash_usd = float(current.get("cash_usd", 0)) - amount_filled
                
                logger.info(
                    f"BUY {asset_amount:.8f} {asset_symbol} @ {price_usd:.2f} USD "
                    f"(spent {amount_filled:.2f} USD)"
                )
            
            elif action == "SELL":
                # Find position to sell
                asset_symbol = pair.split("/")[0] if "/" in pair else pair
                
                if asset_symbol not in positions:
                    raise ValueError(f"No position in {asset_symbol} to sell")
                
                position = positions[asset_symbol]
                sell_quantity = amount_filled / price_usd
                
                if sell_quantity > position["quantity"]:
                    raise ValueError(
                        f"Cannot sell {sell_quantity:.8f} {asset_symbol}: "
                        f"only {position['quantity']:.8f} available"
                    )
                
                # Calculate PnL
                entry_price = position["avg_entry_price"]
                pnl = (price_usd - entry_price) * sell_quantity
                
                # Update position
                position["quantity"] -= sell_quantity
                if position["quantity"] <= 1e-10:  # Account for float precision
                    del positions[asset_symbol]
                
                # Add to cash
                cash_usd = float(current.get("cash_usd", 0)) + amount_filled
                
                logger.info(
                    f"SELL {sell_quantity:.8f} {asset_symbol} @ {price_usd:.2f} USD "
                    f"(received {amount_filled:.2f} USD, PnL: {pnl:.2f} USD)"
                )
            
            else:
                return TradeExecutionOutcome(
                    success=False,
                    message=f"Unknown action: {action}",
                )
            
            # Calculate new total assets
            total_assets = cash_usd
            for symbol, pos in positions.items():
                # This is simplified; in production, fetch current price
                total_assets += pos.get("quantity", 0) * pos.get("avg_entry_price", 0)
            
            # Save to portfolio
            self.portfolio_manager.save_portfolio_state(
                cash_usd=cash_usd,
                positions=positions,
                unrealized_pnl=0.0,  # TODO: calculate from current prices
                realized_pnl=0.0,
                total_assets=total_assets,
            )
            
            # Record in trade history
            self._record_trade_history(
                action=action,
                pair=pair,
                quantity=amount_filled / price_usd if action == "BUY" else amount_filled / price_usd,
                price=price_usd,
                amount_usd=amount_filled,
                status=TradeStatus.APPROVED.value,
                on_chain_hash=approval_event.transaction_hash,
                intent_hash=approval_event.intent_hash,
            )
            
            new_state = {
                "cash_usd": cash_usd,
                "positions": positions,
                "total_assets": total_assets,
            }
            
            return TradeExecutionOutcome(
                success=True,
                message=f"Trade approved and applied: {action} {amount_filled:.2f} USD",
                previous_state=previous_state,
                new_state=new_state,
                pnl_impact=0.0,  # TODO: calculate PnL
            )
        
        except Exception as e:
            logger.error(f"Error applying approved trade: {e}", exc_info=True)
            return TradeExecutionOutcome(
                success=False,
                message=f"Error applying approved trade: {str(e)}",
            )
    
    def apply_rejected_trade(
        self,
        rejection_event: TradeRejectionEvent,
        trade_intent: Dict[str, Any],
    ) -> TradeExecutionOutcome:
        """Handle a rejected trade.
        
        Updates:
        - Revert any reserved capital
        - Record rejection reason in trade history
        - No portfolio positions are modified
        
        Args:
            rejection_event: TradeRejectionEvent from RiskRouter
            trade_intent: Original TradeIntent dict
        
        Returns:
            TradeExecutionOutcome with success status
        """
        try:
            current = self.portfolio_manager.load_latest_portfolio()
            
            action = str(trade_intent.get("action", "")).upper()
            pair = str(trade_intent.get("pair", "UNKNOWN"))
            amount_usd = float(rejection_event.amount_usd_scaled or 0) / 100.0
            reason = rejection_event.rejection_reason
            
            logger.warning(
                f"Trade REJECTED: {action} {pair} {amount_usd:.2f} USD - {reason}"
            )
            
            # Record rejection in trade history
            self._record_trade_history(
                action=action,
                pair=pair,
                quantity=0.0,
                price=0.0,
                amount_usd=amount_usd,
                status=TradeStatus.REJECTED.value,
                on_chain_hash=rejection_event.transaction_hash,
                intent_hash=rejection_event.intent_hash,
                rejection_reason=reason,
            )
            
            # Return current state unchanged
            return TradeExecutionOutcome(
                success=True,
                message=f"Trade rejected: {reason}",
                previous_state=current,
                new_state=current,
            )
        
        except Exception as e:
            logger.error(f"Error applying rejected trade: {e}", exc_info=True)
            return TradeExecutionOutcome(
                success=False,
                message=f"Error applying rejected trade: {str(e)}",
            )
    
    def _record_trade_history(
        self,
        action: str,
        pair: str,
        quantity: float,
        price: float,
        amount_usd: float,
        status: str,
        on_chain_hash: str,
        intent_hash: str,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """Record trade in SQLite trade_history table.
        
        Args:
            action: BUY, SELL, or HOLD
            pair: Trading pair
            quantity: Amount of base asset
            price: Execution price in USD
            amount_usd: USD value
            status: approved, rejected, executed, failed
            on_chain_hash: RiskRouter transaction hash
            intent_hash: TradeIntent hash
            rejection_reason: Reason if rejected
        """
        import sqlite3
        from pathlib import Path
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cur.execute("""
                INSERT INTO trade_history (
                    timestamp, action, pair, quantity, price, amount_usd,
                    status, on_chain_hash, intent_hash, rejection_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, action, pair, quantity, price, amount_usd,
                status, on_chain_hash, intent_hash, rejection_reason
            ))
            
            conn.commit()
            logger.info(
                f"Recorded trade history: {action} {pair} {quantity:.8f} @ {price:.2f} "
                f"[status: {status}]"
            )
        
        except Exception as e:
            logger.error(f"Error recording trade history: {e}")
        finally:
            if conn:
                conn.close()
    
    def get_trade_history(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent trade history.
        
        Args:
            limit: Maximum number of trades to return
        
        Returns:
            List of trade records
        """
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM trade_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Error retrieving trade history: {e}")
            return []
        finally:
            if conn:
                conn.close()


def create_portfolio_feedback_engine(
    portfolio_manager: PortfolioManager,
) -> PortfolioFeedbackEngine:
    """Factory function to create a PortfolioFeedbackEngine.
    
    Args:
        portfolio_manager: PortfolioManager instance
    
    Returns:
        PortfolioFeedbackEngine instance
    """
    return PortfolioFeedbackEngine(portfolio_manager)
