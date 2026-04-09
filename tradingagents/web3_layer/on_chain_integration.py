"""
Automatic on-chain integration for TradingAgents.

This module handles the automatic submission of TradeIntents and Checkpoints
to the Sepolia hackathon contracts after each agent decision.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from tradingagents.web3_layer.client import HackathonWeb3Client

logger = logging.getLogger(__name__)


@dataclass
class OnChainSubmissionResult:
    """Result of an on-chain submission."""
    trade_submitted: bool
    trade_intent_hash: Optional[str] = None
    trade_error: Optional[str] = None
    
    checkpoint_submitted: bool = False
    checkpoint_hash: Optional[str] = None
    checkpoint_error: Optional[str] = None
    
    # Feedback from RiskRouter (populated after waiting for result)
    trade_approved: bool = False
    trade_rejected: bool = False
    approval_event: Optional[Dict[str, Any]] = None
    rejection_event: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    
    metadata: Dict[str, Any] = None  # Additional info about the submission


class TradeIntentAdapter:
    """Adapts agent final decision to TradingRouter's TradeIntent format."""
    
    @staticmethod
    def parse_final_decision(decision_json: str) -> Dict[str, Any]:
        """Parse final trade decision JSON from agent."""
        try:
            return json.loads(decision_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse final decision JSON: {e}")
            return {}
    
    @staticmethod
    def build_trade_intent(
        agent_id: int,
        agent_wallet: str,
        pair: str,
        action: str,
        amount_usd_scaled: int,
        nonce: int,
        deadline: Optional[int] = None,
        max_slippage_bps: int = 100,
    ) -> Dict[str, Any]:
        """Build a TradeIntent from agent decision parameters.
        
        Args:
            agent_id: Agent's ERC-721 token ID
            agent_wallet: Agent's wallet address for signing
            pair: Trading pair (e.g., "XBTUSD", "WETH/USDC")
            action: "BUY", "SELL", or "HOLD"
            amount_usd_scaled: Amount in cents (e.g., $500 = 50000)
            nonce: Current nonce from AgentRegistry
            deadline: Unix timestamp (defaults to now + 5 minutes)
            max_slippage_bps: Maximum slippage in basis points (default 100 = 1%)
        
        Returns:
            TradeIntent dict ready for signing
        """
        if deadline is None:
            deadline = int(time.time()) + 300  # 5 minutes from now
        
        return {
            "agentId": int(agent_id),
            "agentWallet": agent_wallet,
            "pair": pair,
            "action": action.upper(),
            "amountUsdScaled": int(amount_usd_scaled),
            "maxSlippageBps": int(max_slippage_bps),
            "nonce": int(nonce),
            "deadline": int(deadline),
        }
    
    @staticmethod
    def should_submit(
        decision: Dict[str, Any],
        submit_hold_decisions: bool = False,
    ) -> bool:
        """Check if decision warrants on-chain submission.

        By default HOLD actions are skipped unless submit_hold_decisions=True.
        """
        if not decision:
            return False
        
        action = decision.get("action", "").upper()
        if action == "HOLD" and not submit_hold_decisions:
            logger.info("Action is HOLD, skipping on-chain submission")
            return False
        
        order = decision.get("order", {})
        notional = order.get("notional_usd", 0)
        if notional <= 0:
            logger.info(f"Order notional is {notional}, skipping submission")
            return False
        
        return True


class OnChainIntegrator:
    """Orchestrates TradeIntent and Checkpoint submission to chain."""
    
    def __init__(
        self,
        web3_client: HackathonWeb3Client,
        agent_id: int,
        agent_wallet: str,
        checkpoint_score: int = 75,
        enable_simulation: bool = True,
        submit_hold_decisions: bool = False,
        checkpoint_notes_prefix: str = "TradingAgent decision:",
    ):
        """Initialize the on-chain integrator.
        
        Args:
            web3_client: Connected HackathonWeb3Client instance
            agent_id: Agent's registered ID
            agent_wallet: Agent's wallet for signing
            checkpoint_score: Default score for checkpoints (0-100)
            enable_simulation: If True, simulate intents before submission
            submit_hold_decisions: If True, submit HOLD actions to RiskRouter
            checkpoint_notes_prefix: Prefix for checkpoint notes
        """
        self.client = web3_client
        self.agent_id = int(agent_id)
        self.agent_wallet = agent_wallet
        self.checkpoint_score = max(0, min(100, int(checkpoint_score)))
        self.enable_simulation = enable_simulation
        self.submit_hold_decisions = bool(submit_hold_decisions)
        self.checkpoint_notes_prefix = checkpoint_notes_prefix

    @staticmethod
    def _normalize_tx_hash(tx_hash: Any) -> str:
        """Normalize tx hash across providers that return str or bytes-like objects."""
        if tx_hash is None:
            raise ValueError("Missing transaction hash")
        if isinstance(tx_hash, str):
            return tx_hash
        if hasattr(tx_hash, "hex"):
            return tx_hash.hex()
        return str(tx_hash)
    
    def submit_decision(
        self,
        final_decision_json: str,
        current_price_usd_scaled: int = 0,
        trade_date: Optional[str] = None,
    ) -> OnChainSubmissionResult:
        """Submit an agent decision to the on-chain contracts.
        
        This method:
        1. Parses the final decision JSON
        2. Checks if submission is needed (skips HOLD)
        3. Builds and optionally simulates TradeIntent
        4. Signs and submits TradeIntent to RiskRouter
        5. Constructs and submits Checkpoint to ValidationRegistry
        
        Args:
            final_decision_json: JSON string from TradingAgentsGraph.analyze()
            current_price_usd_scaled: Current price in cents (used for checkpoint)
            trade_date: Optional trade date for logging
        
        Returns:
            OnChainSubmissionResult with submission status and hashes
        """
        result = OnChainSubmissionResult(
            trade_submitted=False,
            checkpoint_submitted=False,
            metadata={
                "agent_id": self.agent_id,
                "timestamp": int(time.time()),
                "trade_date": trade_date,
            }
        )
        
        # Parse decision
        decision = TradeIntentAdapter.parse_final_decision(final_decision_json)
        if not decision:
            result.trade_error = "Failed to parse final decision JSON"
            logger.error(result.trade_error)
            return result
        
        # Check if we should submit
        if not TradeIntentAdapter.should_submit(
            decision,
            submit_hold_decisions=self.submit_hold_decisions,
        ):
            result.metadata["submission_skipped"] = True
            return result
        
        # Extract parameters (prefer structured TradeIntent from risk engine)
        trade_intent = decision.get("trade_intent", {}) if isinstance(decision, dict) else {}
        action = str(trade_intent.get("action", decision.get("action", "HOLD"))).upper()
        pair = self._normalize_pair(str(trade_intent.get("pair", "")))

        order = decision.get("order", {})
        if not pair or pair == "UNKNOWN":
            ticker = order.get("ticker", "UNKNOWN")
            pair = self._normalize_pair(ticker)

        # Prefer on-chain scaled cents; fallback to legacy notional_usd (USD float)
        if "amountUsdScaled" in trade_intent:
            amount_usd_scaled = int(trade_intent.get("amountUsdScaled", 0))
        else:
            amount_usd_scaled = int(float(order.get("notional_usd", 0)) * 100)

        max_slippage_bps = int(trade_intent.get("maxSlippageBps", 100))
        intent_deadline = trade_intent.get("deadline")
        intent_deadline = int(intent_deadline) if intent_deadline is not None else None
        reasoning = decision.get("reason", "")
        
        logger.info(
            f"Submitting on-chain: action={action}, pair={pair}, "
            f"amount={amount_usd_scaled/100:.2f} USD"
        )
        
        try:
            # RiskRouter validates TradeIntent against its own intent nonce.
            nonce = self.client.get_intent_nonce(self.agent_id)
            
            # Build TradeIntent
            intent = TradeIntentAdapter.build_trade_intent(
                agent_id=self.agent_id,
                agent_wallet=self.agent_wallet,
                pair=pair,
                action=action,
                amount_usd_scaled=amount_usd_scaled,
                nonce=nonce,
                deadline=intent_deadline,
                max_slippage_bps=max_slippage_bps,
            )
            
            # Simulate if enabled
            if self.enable_simulation:
                is_valid, reason = self.client.simulate_intent(intent)
                if not is_valid:
                    result.trade_error = f"Simulation failed: {reason}"
                    logger.warning(result.trade_error)
                    return result
                logger.info(f"Intent simulation successful: {reason}")
            
            # Sign and submit
            signature = self.client.sign_trade_intent(intent)
            tx_result = self.client.submit_trade_intent(intent, signature)

            result.trade_intent_hash = self._normalize_tx_hash(tx_result.tx_hash)
            result.trade_submitted = True
            logger.info(f"TradeIntent submitted: {result.trade_intent_hash}")
            
            result.metadata["trade_intent"] = intent
            result.metadata["intent_nonce"] = nonce
            
        except Exception as e:
            result.trade_error = f"TradeIntent submission failed: {str(e)}"
            logger.error(result.trade_error, exc_info=True)
            return result
        
        # Submit checkpoint (best effort, doesn't block if fails)
        try:
            checkpoint_hash, checkpoint_dict = self.client.build_checkpoint_hash(
                agent_id=self.agent_id,
                action=action,
                pair=pair,
                amount_usd_scaled=amount_usd_scaled,
                price_usd_scaled=current_price_usd_scaled,
                reasoning=reasoning,
            )
            
            # Build notes/score from trader metadata
            confidence_raw = decision.get("confidence", 0.5)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))
            notes = reasoning.strip() if reasoning else f"{self.checkpoint_notes_prefix} action={action}"
            score = int(round(confidence * 100))
            
            # Submit checkpoint
            checkpoint_tx = self.client.post_checkpoint_attestation(
                agent_id=self.agent_id,
                checkpoint_hash=checkpoint_hash,
                score=score,
                notes=notes,
            )

            result.checkpoint_submitted = True
            result.checkpoint_hash = self._normalize_tx_hash(checkpoint_tx.tx_hash)
            logger.info(f"Checkpoint submitted: {result.checkpoint_hash}")
            
            result.metadata["checkpoint"] = checkpoint_dict
            result.metadata["checkpoint_hash"] = checkpoint_hash
            result.metadata["checkpoint_notes"] = notes
            result.metadata["checkpoint_score"] = score
            
        except Exception as e:
            result.checkpoint_error = f"Checkpoint submission failed: {str(e)}"
            logger.error(result.checkpoint_error, exc_info=True)
            # Don't fail the whole operation if checkpoint fails
        
        return result
    
    def wait_for_feedback(
        self,
        submission_result: OnChainSubmissionResult,
        max_wait_seconds: int = 300,
        poll_interval_seconds: int = 5,
    ) -> OnChainSubmissionResult:
        """Wait for and collect RiskRouter feedback (approval/rejection).
        
        This method polls RiskRouter events until the submitted trade receives
        approval or rejection, or until timeout.
        
        Args:
            submission_result: Result from submit_decision()
            max_wait_seconds: Maximum time to wait (default 5 minutes)
            poll_interval_seconds: Time between polls (default 5 seconds)
        
        Returns:
            Updated submission_result with approval/rejection feedback
        """
        if not submission_result.trade_submitted:
            logger.warning("No trade was submitted, skipping feedback wait")
            return submission_result

        if not submission_result.trade_intent_hash:
            logger.warning("No trade intent hash in submission result, skipping feedback wait")
            if not submission_result.metadata:
                submission_result.metadata = {}
            submission_result.metadata["feedback_skipped_no_intent_hash"] = True
            return submission_result
        
        try:
            from tradingagents.web3_layer.trade_status_checker import (
                create_trade_status_checker,
            )
            
            checker = create_trade_status_checker(self.client)
            intent_hash = submission_result.trade_intent_hash
            
            logger.info(
                f"Waiting for RiskRouter feedback on trade {intent_hash[:16]}... "
                f"(timeout: {max_wait_seconds}s)"
            )
            
            result = checker.poll_trade_result(
                agent_id=self.agent_id,
                intent_hash=intent_hash,
                max_wait_seconds=max_wait_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
            
            if result:
                if result["status"] == "approved":
                    submission_result.trade_approved = True
                    submission_result.approval_event = result.get("event")
                    logger.info(f"Trade APPROVED: {intent_hash[:16]}...")
                
                elif result["status"] == "rejected":
                    submission_result.trade_rejected = True
                    submission_result.rejection_event = result.get("event")
                    submission_result.rejection_reason = result.get("reason", "Unknown")
                    logger.warning(
                        f"Trade REJECTED: {intent_hash[:16]}... - {submission_result.rejection_reason}"
                    )
            else:
                logger.warning(
                    f"No feedback received for trade {intent_hash[:16]}... "
                    f"within {max_wait_seconds}s"
                )
                if not submission_result.metadata:
                    submission_result.metadata = {}
                submission_result.metadata["feedback_timeout"] = True
        
        except Exception as e:
            logger.error(f"Error waiting for feedback: {e}", exc_info=True)
            if not submission_result.metadata:
                submission_result.metadata = {}
            submission_result.metadata["feedback_error"] = str(e)
        
        return submission_result
    
    @staticmethod
    def _normalize_pair(ticker: str) -> str:
        """Normalize ticker to pair format.
        
        Examples:
            "WETH/USDC" -> "WETH/USDC"
            "XBTUSD" -> "XBTUSD"
            "weth" -> "WETH/USDC" (if applicable)
        """
        if not ticker:
            return "UNKNOWN"
        
        ticker = ticker.upper().strip()
        
        # Already normalized (contains /)
        if "/" in ticker:
            return ticker
        
        # Common mappings for single tokens
        single_token_pairs = {
            "WETH": "WETH/USDC",
            "ETH": "WETH/USDC",
            "USDC": "USDC/USD",
            "USDT": "USDT/USD",
        }
        
        if ticker in single_token_pairs:
            return single_token_pairs[ticker]
        
        # Default: assume it's already a valid pair
        return ticker


def create_on_chain_integrator(
    rpc_url: Optional[str] = None,
    operator_private_key: Optional[str] = None,
    agent_private_key: Optional[str] = None,
    agent_id: Optional[int] = None,
    agent_wallet: Optional[str] = None,
    enable_simulation: bool = True,
    submit_hold_decisions: bool = False,
) -> Optional[OnChainIntegrator]:
    """Factory function to create an OnChainIntegrator from environment variables.
    
    Environment variables read:
    - SEPOLIA_RPC_URL: RPC endpoint
    - OPERATOR_PRIVATE_KEY: Operator wallet private key
    - AGENT_WALLET_PRIVATE_KEY: Agent wallet private key for signing intents
    - AGENT_ID: Agent's registered ID
    - AGENT_WALLET: Agent's wallet address
    
    All parameters can override environment variables.
    
    Returns:
        OnChainIntegrator instance, or None if required variables missing
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    rpc_url = rpc_url or os.getenv("SEPOLIA_RPC_URL")
    operator_key = operator_private_key or os.getenv("OPERATOR_PRIVATE_KEY")
    agent_key = agent_private_key or os.getenv("AGENT_WALLET_PRIVATE_KEY")
    agent_id = agent_id or os.getenv("AGENT_ID")
    agent_wallet = agent_wallet or os.getenv("AGENT_WALLET_ADDRESS")
    
    if not all([rpc_url, operator_key, agent_key, agent_id, agent_wallet]):
        missing = []
        if not rpc_url:
            missing.append("SEPOLIA_RPC_URL")
        if not operator_key:
            missing.append("OPERATOR_PRIVATE_KEY")
        if not agent_key:
            missing.append("AGENT_WALLET_PRIVATE_KEY")
        if not agent_id:
            missing.append("AGENT_ID")
        if not agent_wallet:
            missing.append("AGENT_WALLET")
        
        logger.warning(
            f"Cannot create OnChainIntegrator: missing environment variables {missing}. "
            "On-chain submission will be disabled."
        )
        return None
    
    try:
        client = HackathonWeb3Client(
            rpc_url=rpc_url,
            operator_private_key=operator_key,
            agent_private_key=agent_key,
        )
        
        integrator = OnChainIntegrator(
            web3_client=client,
            agent_id=int(agent_id),
            agent_wallet=agent_wallet,
            enable_simulation=enable_simulation,
            submit_hold_decisions=submit_hold_decisions,
        )
        
        logger.info(f"OnChainIntegrator initialized for agent {agent_id}")
        return integrator
        
    except Exception as e:
        logger.error(f"Failed to initialize OnChainIntegrator: {e}", exc_info=True)
        return None
