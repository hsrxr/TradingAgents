"""Web3 integration layer for ERC-8004 hackathon shared contracts."""

from .client import HackathonWeb3Client
from .on_chain_integration import (
    OnChainIntegrator,
    OnChainSubmissionResult,
    TradeIntentAdapter,
    create_on_chain_integrator,
)
from .trade_status_checker import (
    TradeStatusChecker,
    TradeApprovalEvent,
    TradeRejectionEvent,
    TradeStatus,
    create_trade_status_checker,
)
from .portfolio_feedback import (
    PortfolioFeedbackEngine,
    TradeExecutionOutcome,
    create_portfolio_feedback_engine,
)

__all__ = [
    "HackathonWeb3Client",
    "OnChainIntegrator",
    "OnChainSubmissionResult",
    "TradeIntentAdapter",
    "create_on_chain_integrator",
    "TradeStatusChecker",
    "TradeApprovalEvent",
    "TradeRejectionEvent",
    "TradeStatus",
    "create_trade_status_checker",
    "PortfolioFeedbackEngine",
    "TradeExecutionOutcome",
    "create_portfolio_feedback_engine",
]
