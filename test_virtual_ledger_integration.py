#!/usr/bin/env python3
"""
Test script for virtual ledger integration with OnChainIntegrator.

This tests:
1. Virtual ledger initialization and basic operations
2. Trade submission and recording
3. Trade approval/rejection feedback processing
4. Balance tracking throughout lifecycle
"""

import json
import tempfile
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test virtual ledger directly
def test_virtual_ledger():
    """Test virtual ledger operations."""
    from tradingagents.virtual_ledger import create_virtual_ledger
    
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.json"
        ledger = create_virtual_ledger(ledger_path=str(ledger_path))
        
        logger.info("=== Testing Virtual Ledger ===")
        
        # Check initial balance
        balance = ledger.get_balance()
        logger.info(f"Initial balance: ${balance:.2f}")
        assert balance == 100000.0, f"Expected 100000, got {balance}"
        
        # Submit a trade
        trade_id1 = ledger.submit_trade(
            agent_id=1,
            pair="WETH/USDC",
            action="BUY",
            amount_usd=5000.0,
            intent_hash="0xabc123",
            confidence=0.85,
            notes="Test BUY trade"
        )
        logger.info(f"Trade submitted: {trade_id1}")
        
        # Submit another trade
        trade_id2 = ledger.submit_trade(
            agent_id=1,
            pair="WETH/USDC",
            action="SELL",
            amount_usd=3000.0,
            intent_hash="0xdef456",
            confidence=0.75,
            notes="Test SELL trade"
        )
        logger.info(f"Trade submitted: {trade_id2}")
        
        # Check balance after submission (reserved)
        balance = ledger.get_balance()
        logger.info(f"Balance after submission (reserved): ${balance:.2f}")
        expected_reserved = 100000.0 - 5000.0 - 3000.0
        assert balance == expected_reserved, f"Expected {expected_reserved}, got {balance}"
        
        # Approve first trade
        ledger.approve_trade("0xabc123")
        logger.info("First trade approved")
        
        # Reject second trade
        ledger.reject_trade("0xdef456", reason="Price too volatile")
        logger.info("Second trade rejected")
        
        # Check final balance (rejected trade balance returned)
        balance = ledger.get_balance()
        logger.info(f"Final balance: ${balance:.2f}")
        expected_final = 100000.0 - 5000.0  # Only BUY approved, SELL rejected so returned
        assert balance == expected_final, f"Expected {expected_final}, got {balance}"
        
        # Get full ledger
        ledger_data = ledger.get_ledger()
        logger.info(f"Ledger entries: {len(ledger_data['trades'])}")
        
        logger.info("[PASS] Virtual ledger tests passed!\n")
        return True


def test_on_chain_integrator_integration():
    """Test OnChainIntegrator integration with virtual ledger."""
    from tradingagents.web3_layer.on_chain_integration import OnChainIntegrator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("=== Testing OnChainIntegrator Integration ===")
        
        # Mock the web3 client
        mock_client = MagicMock()
        
        # Create OnChainIntegrator with test ledger
        ledger_path = Path(tmpdir) / "on_chain_ledger.json"
        integrator = OnChainIntegrator(
            web3_client=mock_client,
            agent_id=1,
            agent_wallet="0xtest_wallet",
            checkpoint_score=75,
            enable_simulation=False,
            submit_hold_decisions=True,
            ledger_path=str(ledger_path)
        )
        
        logger.info(f"OnChainIntegrator initialized with ledger at {ledger_path}")
        logger.info(f"Initial balance: ${integrator.ledger.get_balance():.2f}")
        
        # Verify ledger is properly initialized
        assert integrator.ledger is not None, "Ledger not initialized"
        assert integrator.ledger.get_balance() == 100000.0, "Initial balance incorrect"
        
        logger.info("[PASS] OnChainIntegrator integration tests passed!\n")
        return True


def test_trade_lifecycle():
    """Test full trade lifecycle: submission -> approval -> balance update."""
    from tradingagents.virtual_ledger import create_virtual_ledger
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("=== Testing Trade Lifecycle ===")
        
        ledger_path = Path(tmpdir) / "lifecycle_ledger.json"
        ledger = create_virtual_ledger(ledger_path=str(ledger_path))
        
        # Simulate trade submission
        logger.info("Step 1: Submit BUY trade")
        trade_id = ledger.submit_trade(
            agent_id=1,
            pair="BTCUSD",
            action="BUY",
            amount_usd=50000.0,
            intent_hash="0xlifecycle123",
            confidence=0.90,
            notes="Large BUY position"
        )
        balance_after_submit = ledger.get_balance()
        logger.info(f"  Balance after submit: ${balance_after_submit:.2f} (reserved: $50,000)")
        assert balance_after_submit == 50000.0
        
        # Simulate RiskRouter approval
        logger.info("Step 2: Receive RiskRouter approval")
        ledger.approve_trade("0xlifecycle123")
        balance_after_approval = ledger.get_balance()
        logger.info(f"  Balance after approval: ${balance_after_approval:.2f} (locked)")
        assert balance_after_approval == 50000.0
        
        # Verify trade status
        ledger_data = ledger.get_ledger()
        approved_trades = [t for t in ledger_data['trades'] if t['status'] == 'approved']
        assert len(approved_trades) == 1, "Should have 1 approved trade"
        
        logger.info("[PASS] Trade lifecycle tests passed!\n")
        return True


def test_persistence():
    """Test that ledger data persists across sessions."""
    from tradingagents.virtual_ledger import create_virtual_ledger
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("=== Testing Persistence ===")
        
        ledger_path = Path(tmpdir) / "persist_ledger.json"
        
        # Session 1: Create ledger and add trades
        logger.info("Session 1: Creating trades")
        ledger1 = create_virtual_ledger(ledger_path=str(ledger_path))
        trade_id = ledger1.submit_trade(
            agent_id=1,
            pair="ETHUSD",
            action="BUY",
            amount_usd=25000.0,
            intent_hash="0xpersist123",
            confidence=0.80,
            notes="Persistent trade"
        )
        ledger1.approve_trade("0xpersist123")
        balance1 = ledger1.get_balance()
        logger.info(f"  Balance in session 1: ${balance1:.2f}")
        
        # Session 2: Load same ledger and verify data
        logger.info("Session 2: Loading same ledger")
        ledger2 = create_virtual_ledger(ledger_path=str(ledger_path))
        balance2 = ledger2.get_balance()
        logger.info(f"  Balance in session 2: ${balance2:.2f}")
        
        assert balance1 == balance2, f"Balance mismatch: {balance1} vs {balance2}"
        
        ledger_data = ledger2.get_ledger()
        assert len(ledger_data['trades']) > 0, "No trades persisted"
        
        logger.info("[PASS] Persistence tests passed!\n")
        return True


def test_multiple_trades():
    """Test tracking multiple sequential trades."""
    from tradingagents.virtual_ledger import create_virtual_ledger
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("=== Testing Multiple Trades ===")
        
        ledger_path = Path(tmpdir) / "multi_ledger.json"
        ledger = create_virtual_ledger(ledger_path=str(ledger_path))
        
        trades = [
            ("WETH/USDC", "BUY", 10000, 0.85),
            ("XRPUSD", "SELL", 5000, 0.70),
            ("BTCUSD", "BUY", 20000, 0.90),
            ("DOGEUSDT", "SELL", 2000, 0.60),
        ]
        
        submitted_trades = []
        for pair, action, amount, confidence in trades:
            trade_id = ledger.submit_trade(
                agent_id=1,
                pair=pair,
                action=action,
                amount_usd=amount,
                intent_hash=f"0x{pair}_{len(submitted_trades)}",
                confidence=confidence,
                notes=f"{action} {pair}"
            )
            submitted_trades.append((trade_id, f"0x{pair}_{len(submitted_trades)}", amount))
            logger.info(f"  Submitted {action} {pair}: ${amount}")
        
        total_reserved = sum(t[2] for t in trades)
        balance = ledger.get_balance()
        logger.info(f"  Total reserved: ${total_reserved:.2f}")
        logger.info(f"  Remaining balance: ${balance:.2f}")
        
        # Approve some trades
        for _, intent_hash, amount in submitted_trades[:2]:
            ledger.approve_trade(intent_hash)
        logger.info(f"  Approved 2 trades")
        
        # Reject some trades
        for _, intent_hash, _ in submitted_trades[2:]:
            ledger.reject_trade(intent_hash, reason="Market conditions")
        logger.info(f"  Rejected 2 trades")
        
        # Check final balance
        final_balance = ledger.get_balance()
        expected = 100000.0 - (trades[0][2] + trades[1][2])  # First 2 approved
        logger.info(f"  Final balance: ${final_balance:.2f} (expected: ${expected:.2f})")
        
        assert final_balance == expected, f"Balance mismatch: {final_balance} vs {expected}"
        
        logger.info("[PASS] Multiple trades tests passed!\n")
        return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Virtual Ledger Integration Test Suite")
    print("="*60 + "\n")
    
    tests = [
        ("Virtual Ledger", test_virtual_ledger),
        ("OnChainIntegrator Integration", test_on_chain_integrator_integration),
        ("Trade Lifecycle", test_trade_lifecycle),
        ("Persistence", test_persistence),
        ("Multiple Trades", test_multiple_trades),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASSED" if result else "FAILED"))
        except Exception as e:
            logger.error(f"Test {name} FAILED: {e}", exc_info=True)
            results.append((name, f"ERROR: {str(e)[:50]}"))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for name, result in results:
        status = "[OK]" if "PASSED" in result else "[FAIL]"
        print(f"{status} {name}: {result}")
    
    passed = sum(1 for _, r in results if "PASSED" in r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
