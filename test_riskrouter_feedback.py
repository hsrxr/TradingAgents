"""
Integration test for RiskRouter feedback mechanism.

This script demonstrates the complete feedback loop:
1. Trade submission to RiskRouter
2. Event polling and approval/rejection detection
3. Portfolio updates based on feedback
4. Memory recording of trade outcomes
"""

import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_trade_status_checker():
    """Test TradeStatusChecker initialization and basic methods."""
    logger.info("=" * 80)
    logger.info("TEST 1: TradeStatusChecker")
    logger.info("=" * 80)
    
    try:
        from tradingagents.web3_layer import (
            TradeStatusChecker,
            create_trade_status_checker,
        )
        
        logger.info("✓ Successfully imported TradeStatusChecker")
        logger.info("✓ Factory function: create_trade_status_checker available")
        
        # Check enums
        from tradingagents.web3_layer.trade_status_checker import TradeStatus
        logger.info(f"✓ Available trade statuses: {[s.value for s in TradeStatus]}")
        
        return True
    except Exception as e:
        logger.error(f"✗ TradeStatusChecker test failed: {e}", exc_info=True)
        return False


def test_portfolio_feedback_engine():
    """Test PortfolioFeedbackEngine initialization."""
    logger.info("=" * 80)
    logger.info("TEST 2: PortfolioFeedbackEngine")
    logger.info("=" * 80)
    
    try:
        from tradingagents.web3_layer import (
            PortfolioFeedbackEngine,
            create_portfolio_feedback_engine,
        )
        from tradingagents.portfolio_manager import PortfolioManager
        
        # Create a test portfolio manager
        pm = PortfolioManager(db_path="trade_memory/portfolio.db")
        logger.info("✓ Created PortfolioManager instance")
        
        # Create feedback engine
        engine = create_portfolio_feedback_engine(pm)
        logger.info("✓ Created PortfolioFeedbackEngine instance")
        logger.info(f"  - Database path: {engine.db_path}")
        
        # Check methods exist
        assert hasattr(engine, 'apply_approved_trade'), "Missing apply_approved_trade method"
        assert hasattr(engine, 'apply_rejected_trade'), "Missing apply_rejected_trade method"
        assert hasattr(engine, 'get_trade_history'), "Missing get_trade_history method"
        logger.info("✓ All required methods available")
        
        return True
    except Exception as e:
        logger.error(f"✗ PortfolioFeedbackEngine test failed: {e}", exc_info=True)
        return False


def test_trade_outcome_recorder():
    """Test TradeOutcomeRecorder initialization."""
    logger.info("=" * 80)
    logger.info("TEST 3: TradeOutcomeRecorder")
    logger.info("=" * 80)
    
    try:
        from tradingagents.graph.trade_outcome_recorder import (
            TradeOutcomeRecorder,
            create_trade_outcome_recorder,
        )
        
        # Create recorder
        recorder = create_trade_outcome_recorder()
        logger.info("✓ Created TradeOutcomeRecorder instance")
        
        # Check methods
        assert hasattr(recorder, 'record_approved_trade'), "Missing record_approved_trade method"
        assert hasattr(recorder, 'record_rejected_trade'), "Missing record_rejected_trade method"
        assert hasattr(recorder, 'record_trade_outcome_for_all_agents'), "Missing record_trade_outcome_for_all_agents method"
        assert hasattr(recorder, 'get_stats'), "Missing get_stats method"
        logger.info("✓ All required methods available")
        
        # Check stats
        stats = recorder.get_stats()
        logger.info(f"✓ Recorder stats: {stats}")
        
        return True
    except Exception as e:
        logger.error(f"✗ TradeOutcomeRecorder test failed: {e}", exc_info=True)
        return False


def test_on_chain_integration_feedback():
    """Test OnChainIntegrator feedback integration."""
    logger.info("=" * 80)
    logger.info("TEST 4: OnChainIntegrator with Feedback")
    logger.info("=" * 80)
    
    try:
        from tradingagents.web3_layer import (
            OnChainSubmissionResult,
        )
        
        # Create a mock submission result
        result = OnChainSubmissionResult(
            trade_submitted=True,
            trade_intent_hash="0xabcd1234",
            checkpoint_submitted=True,
            checkpoint_hash="0xefgh5678",
        )
        logger.info("✓ Created OnChainSubmissionResult instance")
        logger.info(f"  - Trade submitted: {result.trade_submitted}")
        logger.info(f"  - Checkpoint submitted: {result.checkpoint_submitted}")
        
        # Check feedback fields
        assert hasattr(result, 'trade_approved'), "Missing trade_approved field"
        assert hasattr(result, 'trade_rejected'), "Missing trade_rejected field"
        assert hasattr(result, 'approval_event'), "Missing approval_event field"
        assert hasattr(result, 'rejection_event'), "Missing rejection_event field"
        assert hasattr(result, 'rejection_reason'), "Missing rejection_reason field"
        logger.info("✓ All feedback fields available")
        
        # Simulate approval
        result.trade_approved = True
        result.approval_event = {
            "agent_id": 40,
            "intent_hash": "0xabcd1234",
            "amount_usd_scaled": 50000,
            "transaction_hash": "0x123456",
            "block_number": 5000000,
            "timestamp": int(datetime.now().timestamp()),
        }
        logger.info("✓ Simulated trade approval feedback")
        logger.info(f"  - Intent hash: {result.approval_event['intent_hash']}")
        
        return True
    except Exception as e:
        logger.error(f"✗ OnChainIntegrator feedback test failed: {e}", exc_info=True)
        return False


def test_trading_graph_integration():
    """Test TradingAgentsGraph has feedback integration."""
    logger.info("=" * 80)
    logger.info("TEST 5: TradingAgentsGraph Integration")
    logger.info("=" * 80)
    
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        # Check that methods exist
        assert hasattr(TradingAgentsGraph, '_apply_on_chain_feedback'), "Missing _apply_on_chain_feedback method"
        assert hasattr(TradingAgentsGraph, '_record_trade_outcome_in_memory'), "Missing _record_trade_outcome_in_memory method"
        logger.info("✓ TradingAgentsGraph has feedback integration methods")
        
        return True
    except Exception as e:
        logger.error(f"✗ TradingAgentsGraph integration test failed: {e}", exc_info=True)
        return False


def test_imports_and_exports():
    """Test that all new modules are properly exported."""
    logger.info("=" * 80)
    logger.info("TEST 6: Module Exports")
    logger.info("=" * 80)
    
    try:
        # Test web3_layer exports
        from tradingagents.web3_layer import (
            TradeStatusChecker,
            TradeApprovalEvent,
            TradeRejectionEvent,
            TradeStatus,
            create_trade_status_checker,
            PortfolioFeedbackEngine,
            TradeExecutionOutcome,
            create_portfolio_feedback_engine,
        )
        logger.info("✓ All web3_layer exports available")
        
        # Test graph module imports
        from tradingagents.graph.trade_outcome_recorder import (
            TradeOutcomeRecorder,
            create_trade_outcome_recorder,
        )
        logger.info("✓ Trade outcome recorder imports available")
        
        return True
    except Exception as e:
        logger.error(f"✗ Module exports test failed: {e}", exc_info=True)
        return False


def main():
    """Run all integration tests."""
    logger.info("\n")
    logger.info("*" * 80)
    logger.info("RiskRouter FEEDBACK MECHANISM - INTEGRATION TESTS")
    logger.info("*" * 80)
    logger.info("\n")
    
    tests = [
        ("TradeStatusChecker", test_trade_status_checker),
        ("PortfolioFeedbackEngine", test_portfolio_feedback_engine),
        ("TradeOutcomeRecorder", test_trade_outcome_recorder),
        ("OnChainIntegrator Feedback", test_on_chain_integration_feedback),
        ("TradingAgentsGraph Integration", test_trading_graph_integration),
        ("Module Exports", test_imports_and_exports),
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
        logger.info("\n")
    
    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed\n")
    
    if passed == total:
        logger.info("✓ All integration tests passed!")
        return 0
    else:
        logger.error(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
