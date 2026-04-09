"""
Monitor and retrieve RiskRouter trade approval/rejection events.

This module provides functionality to:
1. Query TradeApproved and TradeRejected events from RiskRouter
2. Track pending trade intents and their outcomes
3. Provide feedback for portfolio and memory updates
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum

from tradingagents.web3_layer.client import HackathonWeb3Client

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Possible trade approval statuses."""
    PENDING = "pending"           # Submitted but not yet approved/rejected
    APPROVED = "approved"         # Approved by RiskRouter
    REJECTED = "rejected"         # Rejected by RiskRouter
    EXECUTED = "executed"         # Approved and executed on DEX
    FAILED = "failed"             # Execution failed after approval


@dataclass
class TradeApprovalEvent:
    """Represents a trade approval event from RiskRouter."""
    agent_id: int
    intent_hash: str
    amount_usd_scaled: int
    nonce: int
    block_number: int
    transaction_hash: str
    timestamp: int
    
    status: TradeStatus = TradeStatus.APPROVED
    execution_details: Optional[Dict[str, Any]] = None  # DEX execution info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "agent_id": self.agent_id,
            "intent_hash": self.intent_hash,
            "amount_usd_scaled": self.amount_usd_scaled,
            "nonce": self.nonce,
            "block_number": self.block_number,
            "transaction_hash": self.transaction_hash,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "execution_details": self.execution_details,
        }


@dataclass
class TradeRejectionEvent:
    """Represents a trade rejection event from RiskRouter."""
    agent_id: int
    intent_hash: str
    rejection_reason: str
    nonce: int
    block_number: int
    transaction_hash: str
    timestamp: int
    
    status: TradeStatus = TradeStatus.REJECTED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "agent_id": self.agent_id,
            "intent_hash": self.intent_hash,
            "rejection_reason": self.rejection_reason,
            "nonce": self.nonce,
            "block_number": self.block_number,
            "transaction_hash": self.transaction_hash,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


class TradeStatusChecker:
    """Query and monitor trade approval/rejection status from RiskRouter."""
    
    def __init__(self, client: HackathonWeb3Client):
        """Initialize with a connected Web3 client.
        
        Args:
            client: HackathonWeb3Client instance
        """
        self.client = client
        self.contract = client.risk_router
        self.w3 = client.w3
        
        # Cache of known events to avoid re-processing
        self._approval_cache: Dict[str, TradeApprovalEvent] = {}
        self._rejection_cache: Dict[str, TradeRejectionEvent] = {}
        self._last_block_checked = 0
    
    def get_approval_events(
        self,
        agent_id: int,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> List[TradeApprovalEvent]:
        """Retrieve TradeApproved events for an agent.
        
        Args:
            agent_id: Agent ID to filter by
            from_block: Start block (defaults to last checked block)
            to_block: End block (defaults to latest block)
        
        Returns:
            List of TradeApprovalEvent objects
        """
        try:
            if from_block is None:
                from_block = max(0, self._last_block_checked - 100)
            if to_block is None:
                to_block = "latest"
            
            # Query TradeApproved events
            events = self.contract.events.TradeApproved.get_logs(
                from_block=from_block,
                to_block=to_block,
                argument_filters={"agentId": agent_id},
            )
            
            approval_events = []
            for event in events:
                try:
                    approval_obj = TradeApprovalEvent(
                        agent_id=event["args"]["agentId"],
                        intent_hash=event["args"]["intentHash"].hex(),
                        amount_usd_scaled=event["args"]["amountUsdScaled"],
                        nonce=0,  # Not in event, will be fetched separately if needed
                        block_number=event["blockNumber"],
                        transaction_hash=event["transactionHash"].hex(),
                        timestamp=self._get_block_timestamp(event["blockNumber"]),
                    )
                    approval_events.append(approval_obj)
                    self._approval_cache[approval_obj.intent_hash] = approval_obj
                    
                except Exception as e:
                    logger.error(f"Failed to parse TradeApproved event: {e}")
                    continue
            
            # Update last block checked
            if events:
                self._last_block_checked = max(e["blockNumber"] for e in events)
            
            logger.info(f"Found {len(approval_events)} approval events for agent {agent_id}")
            return approval_events
            
        except Exception as e:
            logger.error(f"Error querying TradeApproved events: {e}")
            return []
    
    def get_rejection_events(
        self,
        agent_id: int,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> List[TradeRejectionEvent]:
        """Retrieve TradeRejected events for an agent.
        
        Args:
            agent_id: Agent ID to filter by
            from_block: Start block (defaults to last checked block)
            to_block: End block (defaults to latest block)
        
        Returns:
            List of TradeRejectionEvent objects
        """
        try:
            if from_block is None:
                from_block = max(0, self._last_block_checked - 100)
            if to_block is None:
                to_block = "latest"
            
            # Query TradeRejected events
            events = self.contract.events.TradeRejected.get_logs(
                from_block=from_block,
                to_block=to_block,
                argument_filters={"agentId": agent_id},
            )
            
            rejection_events = []
            for event in events:
                try:
                    rejection_obj = TradeRejectionEvent(
                        agent_id=event["args"]["agentId"],
                        intent_hash=event["args"]["intentHash"].hex(),
                        rejection_reason=event["args"]["reason"],
                        nonce=0,  # Not in event
                        block_number=event["blockNumber"],
                        transaction_hash=event["transactionHash"].hex(),
                        timestamp=self._get_block_timestamp(event["blockNumber"]),
                    )
                    rejection_events.append(rejection_obj)
                    self._rejection_cache[rejection_obj.intent_hash] = rejection_obj
                    
                except Exception as e:
                    logger.error(f"Failed to parse TradeRejected event: {e}")
                    continue
            
            # Update last block checked
            if events:
                self._last_block_checked = max(e["blockNumber"] for e in events)
            
            logger.info(f"Found {len(rejection_events)} rejection events for agent {agent_id}")
            return rejection_events
            
        except Exception as e:
            logger.error(f"Error querying TradeRejected events: {e}")
            return []
    
    def poll_trade_result(
        self,
        agent_id: int,
        intent_hash: str,
        max_wait_seconds: int = 300,
        poll_interval_seconds: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Poll for a specific trade's approval/rejection result.
        
        This is a blocking call that polls RiskRouter events until the trade
        is approved/rejected or timeout is reached.
        
        Args:
            agent_id: Agent ID
            intent_hash: The intent hash to wait for
            max_wait_seconds: Maximum time to wait (default 5 minutes)
            poll_interval_seconds: Time between polls (default 5 seconds)
        
        Returns:
            Result dict with status, event details, or None on timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            # Check approvals
            if intent_hash in self._approval_cache:
                event = self._approval_cache[intent_hash]
                logger.info(f"Trade {intent_hash} APPROVED")
                return {
                    "status": TradeStatus.APPROVED.value,
                    "event": event.to_dict(),
                }
            
            # Check rejections
            if intent_hash in self._rejection_cache:
                event = self._rejection_cache[intent_hash]
                logger.info(f"Trade {intent_hash} REJECTED: {event.rejection_reason}")
                return {
                    "status": TradeStatus.REJECTED.value,
                    "event": event.to_dict(),
                    "reason": event.rejection_reason,
                }
            
            # Query latest events
            approvals = self.get_approval_events(agent_id)
            rejections = self.get_rejection_events(agent_id)
            
            # Check again after fresh query
            if intent_hash in self._approval_cache:
                event = self._approval_cache[intent_hash]
                logger.info(f"Trade {intent_hash} APPROVED (via fresh query)")
                return {
                    "status": TradeStatus.APPROVED.value,
                    "event": event.to_dict(),
                }
            
            if intent_hash in self._rejection_cache:
                event = self._rejection_cache[intent_hash]
                logger.info(f"Trade {intent_hash} REJECTED (via fresh query): {event.rejection_reason}")
                return {
                    "status": TradeStatus.REJECTED.value,
                    "event": event.to_dict(),
                    "reason": event.rejection_reason,
                }
            
            elapsed = time.time() - start_time
            remaining = max_wait_seconds - elapsed
            logger.info(
                f"Waiting for trade {intent_hash[:16]}... "
                f"({elapsed:.0f}s / {max_wait_seconds}s)"
            )
            
            time.sleep(poll_interval_seconds)
        
        logger.warning(f"Trade {intent_hash} poll timeout after {max_wait_seconds}s")
        return None
    
    def get_pending_trades(
        self,
        agent_id: int,
        submitted_nonces: Optional[List[int]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """Get status of trades potentially still pending.
        
        Args:
            agent_id: Agent ID
            submitted_nonces: Optional list of nonces that were submitted
        
        Returns:
            Dict mapping nonce -> {status, approval_event, rejection_event}
        """
        approvals = self.get_approval_events(agent_id)
        rejections = self.get_rejection_events(agent_id)
        
        pending_status = {}
        
        # Index by nonce if available
        for approval in approvals:
            if approval.nonce not in pending_status:
                pending_status[approval.nonce] = {}
            pending_status[approval.nonce]["status"] = TradeStatus.APPROVED.value
            pending_status[approval.nonce]["approval_event"] = approval.to_dict()
        
        for rejection in rejections:
            if rejection.nonce not in pending_status:
                pending_status[rejection.nonce] = {}
            pending_status[rejection.nonce]["status"] = TradeStatus.REJECTED.value
            pending_status[rejection.nonce]["rejection_event"] = rejection.to_dict()
        
        return pending_status
    
    def _get_block_timestamp(self, block_number: int) -> int:
        """Get block timestamp.
        
        Args:
            block_number: Block number
        
        Returns:
            Unix timestamp
        """
        try:
            block = self.w3.eth.get_block(block_number)
            return int(block["timestamp"])
        except Exception as e:
            logger.warning(f"Failed to get block timestamp for {block_number}: {e}")
            return int(time.time())
    
    def clear_caches(self) -> None:
        """Clear internal event caches."""
        self._approval_cache.clear()
        self._rejection_cache.clear()
        logger.info("Trade status checker caches cleared")


def create_trade_status_checker(client: HackathonWeb3Client) -> TradeStatusChecker:
    """Factory function to create a TradeStatusChecker.
    
    Args:
        client: HackathonWeb3Client instance
    
    Returns:
        TradeStatusChecker instance
    """
    return TradeStatusChecker(client)
