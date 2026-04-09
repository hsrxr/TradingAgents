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
from web3._utils.events import get_event_data
from hexbytes import HexBytes

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
        self.risk_router_address = self.contract.address
        
        # Cache of known events to avoid re-processing
        self._approval_cache: Dict[str, TradeApprovalEvent] = {}
        self._rejection_cache: Dict[str, TradeRejectionEvent] = {}
        self._last_block_checked = 0
        self._max_block_range = 50000

    def _build_topic_filter(self, event_name: str, agent_id: int) -> List[HexBytes]:
        """Build topic[0]/topic[1] for eth_getLogs with indexed agentId filter."""
        signatures = {
            "TradeApproved": "TradeApproved(uint256,bytes32,uint256)",
            "TradeRejected": "TradeRejected(uint256,bytes32,string)",
        }
        signature = signatures.get(event_name)
        if not signature:
            raise ValueError(f"Unsupported event name for topic filter: {event_name}")

        event_topic = HexBytes(self.w3.keccak(text=signature))
        agent_topic = HexBytes(int(agent_id).to_bytes(32, byteorder="big", signed=False))
        return [event_topic, agent_topic]

    def _decode_raw_logs(self, logs: List[Any], event_name: str) -> List[Any]:
        """Decode raw logs from eth_getLogs into event objects compatible with downstream parsing."""
        event_factory = getattr(self.contract.events, event_name)
        event_abi = event_factory().abi

        decoded = []
        for log in logs:
            try:
                decoded.append(get_event_data(self.w3.codec, event_abi, log))
            except Exception as decode_error:
                try:
                    decoded.append(event_factory().process_log(log))
                except Exception as process_error:
                    logger.debug(
                        "Failed to decode %s log via get_event_data/process_log: %s | %s",
                        event_name,
                        decode_error,
                        process_error,
                    )
        return decoded

    def _fetch_logs_via_rpc(
        self,
        event_name: str,
        agent_id: int,
        from_block: int,
        to_block: int,
    ) -> List[Any]:
        """Query logs via eth_getLogs and decode them to event entries."""
        logs = self.client.w3.eth.get_logs(
            {
                "address": self.risk_router_address,
                "topics": self._build_topic_filter(event_name, agent_id),
                "fromBlock": from_block,
                "toBlock": to_block,
            }
        )
        return self._decode_raw_logs(logs, event_name)

    def _resolve_block_window(
        self,
        from_block: Optional[int],
        to_block: Optional[int],
    ) -> tuple[int, int]:
        """Resolve a safe [from_block, to_block] range for RPC providers with range limits."""
        latest_block = int(self.w3.eth.block_number)
        resolved_to = latest_block if to_block is None else int(to_block)

        if from_block is None:
            # If we have progressed before, continue from there; otherwise query a bounded recent window.
            if self._last_block_checked > 0:
                resolved_from = max(0, self._last_block_checked - 100)
            else:
                resolved_from = max(0, resolved_to - self._max_block_range + 1)
        else:
            resolved_from = max(0, int(from_block))

        max_span = self._max_block_range - 1
        if (resolved_to - resolved_from) > max_span:
            adjusted_from = max(0, resolved_to - max_span)
            logger.warning(
                "Adjusting log query window from [%s, %s] to [%s, %s] to satisfy provider max range %s",
                resolved_from,
                resolved_to,
                adjusted_from,
                resolved_to,
                self._max_block_range,
            )
            resolved_from = adjusted_from

        return resolved_from, resolved_to
    
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
            from_block, to_block = self._resolve_block_window(from_block, to_block)
            
            # Query TradeApproved events using proper filter
            try:
                event_filter = self.contract.events.TradeApproved.create_filter(
                    from_block=from_block,
                    to_block=to_block,
                    argument_filters={"agentId": agent_id}
                )
                events = event_filter.get_all_entries()
            except Exception as filter_error:
                # Fallback: use raw RPC logs with explicit topic filters.
                logger.debug("TradeApproved create_filter failed; fallback to eth_getLogs: %s", filter_error)
                try:
                    events = self._fetch_logs_via_rpc(
                        "TradeApproved",
                        agent_id,
                        from_block,
                        to_block,
                    )
                except Exception as eth_error:
                    logger.error("TradeApproved eth_getLogs failed: %s", eth_error)
                    events = []
            
            approval_events = []
            for event in events:
                try:
                    # Handle both dict and Log object formats
                    event_args = event.get("args") if isinstance(event, dict) else event.args
                    if event_args is None:
                        continue
                    if int(event_args.get("agentId", -1)) != int(agent_id):
                        continue

                    intent_hash = event_args["intentHash"]
                    if hasattr(intent_hash, "hex"):
                        intent_hash = intent_hash.hex()

                    tx_hash = event.get("transactionHash") if isinstance(event, dict) else event.transactionHash
                    if tx_hash is not None and hasattr(tx_hash, "hex"):
                        tx_hash = tx_hash.hex()

                    block_num = event.get("blockNumber") if isinstance(event, dict) else event.blockNumber
                    if block_num is None:
                        continue
                    block_num = int(block_num)
                    approval_obj = TradeApprovalEvent(
                        agent_id=event_args["agentId"],
                        intent_hash=str(intent_hash),
                        amount_usd_scaled=event_args["amountUsdScaled"],
                        nonce=0,  # Not in event, will be fetched separately if needed
                        block_number=block_num,
                        transaction_hash=str(tx_hash),
                        timestamp=self._get_block_timestamp(block_num),
                    )
                    approval_events.append(approval_obj)
                    self._approval_cache[approval_obj.intent_hash] = approval_obj
                    
                except Exception as e:
                    logger.error(f"Failed to parse TradeApproved event: {e}")
                    continue
            
            # Update last block checked
            if events:
                self._last_block_checked = max(e["blockNumber"] for e in events)
            else:
                self._last_block_checked = max(self._last_block_checked, int(to_block))
            
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
            from_block, to_block = self._resolve_block_window(from_block, to_block)
            
            # Query TradeRejected events using proper filter
            try:
                event_filter = self.contract.events.TradeRejected.create_filter(
                    from_block=from_block,
                    to_block=to_block,
                    argument_filters={"agentId": agent_id}
                )
                events = event_filter.get_all_entries()
            except Exception as filter_error:
                # Fallback: use raw RPC logs with explicit topic filters.
                logger.debug("TradeRejected create_filter failed; fallback to eth_getLogs: %s", filter_error)
                try:
                    events = self._fetch_logs_via_rpc(
                        "TradeRejected",
                        agent_id,
                        from_block,
                        to_block,
                    )
                except Exception as eth_error:
                    logger.error("TradeRejected eth_getLogs failed: %s", eth_error)
                    events = []
            
            rejection_events = []
            for event in events:
                try:
                    # Handle both dict and Log object formats
                    event_args = event.get("args") if isinstance(event, dict) else event.args
                    if event_args is None:
                        continue
                    if int(event_args.get("agentId", -1)) != int(agent_id):
                        continue

                    intent_hash = event_args["intentHash"]
                    if hasattr(intent_hash, "hex"):
                        intent_hash = intent_hash.hex()

                    tx_hash = event.get("transactionHash") if isinstance(event, dict) else event.transactionHash
                    if tx_hash is not None and hasattr(tx_hash, "hex"):
                        tx_hash = tx_hash.hex()

                    block_num = event.get("blockNumber") if isinstance(event, dict) else event.blockNumber
                    if block_num is None:
                        continue
                    block_num = int(block_num)
                    rejection_obj = TradeRejectionEvent(
                        agent_id=event_args["agentId"],
                        intent_hash=str(intent_hash),
                        rejection_reason=event_args["reason"],
                        nonce=0,  # Not in event
                        block_number=block_num,
                        transaction_hash=str(tx_hash),
                        timestamp=self._get_block_timestamp(block_num),
                    )
                    rejection_events.append(rejection_obj)
                    self._rejection_cache[rejection_obj.intent_hash] = rejection_obj
                    
                except Exception as e:
                    logger.error(f"Failed to parse TradeRejected event: {e}")
                    continue
            
            # Update last block checked
            if events:
                self._last_block_checked = max(e["blockNumber"] for e in events)
            else:
                self._last_block_checked = max(self._last_block_checked, int(to_block))
            
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
        
        logger.warning(
            "Trade %s poll timeout after %ss. Explicit reason: no matching TradeApproved/TradeRejected event was found for agent_id=%s within the queried block windows. Potential causes include: tx pending/not mined yet, event not emitted, wrong agent_id or intent_hash, or RPC/indexing delay.",
            intent_hash,
            max_wait_seconds,
            agent_id,
        )
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
            if isinstance(block, dict):
                return int(block.get("timestamp", time.time()))
            return int(getattr(block, "timestamp", time.time()))
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
