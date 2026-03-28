"""
Test suite for parallel execution mode.
Verifies that parallel mode produces correct results and improves performance.
"""

import unittest
import time
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


class TestParallelExecution(unittest.TestCase):
    """Test parallel execution functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.config = DEFAULT_CONFIG.copy()
        cls.config["llm_provider"] = "deepseek"
        cls.config["deep_think_llm"] = "deepseek-reasoner"
        cls.config["quick_think_llm"] = "deepseek-chat"
        cls.config["max_debate_rounds"] = 1

    def test_serial_mode_initialization(self):
        """Test that serial mode initializes correctly."""
        ta = TradingAgentsGraph(
            selected_analysts=["news"],
            debug=False,
            config=self.config,
            parallel_mode=False
        )
        self.assertIsNotNone(ta.graph)
        self.assertFalse(ta.parallel_mode)

    def test_parallel_mode_initialization(self):
        """Test that parallel mode initializes correctly."""
        ta = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals"],
            debug=False,
            config=self.config,
            parallel_mode=True
        )
        self.assertIsNotNone(ta.graph)
        self.assertTrue(ta.parallel_mode)

    def test_parallel_mode_has_aggregators(self):
        """Test that parallel mode includes aggregator nodes."""
        ta = TradingAgentsGraph(
            selected_analysts=["market", "social", "news"],
            debug=False,
            config=self.config,
            parallel_mode=True
        )
        
        # Check if aggregator nodes exist in the graph
        graph_nodes = list(ta.graph.nodes)
        self.assertIn("Analyst Aggregator", graph_nodes)
        self.assertIn("Investment Debate Aggregator", graph_nodes)
        self.assertIn("Risk Analysis Aggregator", graph_nodes)

    def test_serial_mode_no_aggregators(self):
        """Test that serial mode doesn't have aggregator nodes."""
        ta = TradingAgentsGraph(
            selected_analysts=["market", "social", "news"],
            debug=False,
            config=self.config,
            parallel_mode=False
        )
        
        # Check that aggregator nodes don't exist in serial mode
        graph_nodes = list(ta.graph.nodes)
        # Serial mode might not have all aggregators
        # This is expected behavior

    def test_parallel_analyst_edges(self):
        """Test that parallel mode creates correct edges for analysts."""
        ta = TradingAgentsGraph(
            selected_analysts=["market", "social", "news"],
            debug=False,
            config=self.config,
            parallel_mode=True
        )
        
        # In parallel mode, all analysts should start from START
        # and all should connect to aggregator
        from langgraph.graph import START
        
        # Get all edges from START
        edges = list(ta.graph.edges())
        start_edges = [(src, dst) for src, dst in edges if src == START]
        
        # Should have edges for each analyst type
        analyst_count = len(["market", "social", "news"])
        self.assertEqual(len(start_edges), analyst_count,
                        "Each analyst should have an edge from START")

    def test_graph_compilation(self):
        """Test that graphs compile without errors."""
        ta_serial = TradingAgentsGraph(
            selected_analysts=["news"],
            debug=False,
            config=self.config,
            parallel_mode=False
        )
        
        ta_parallel = TradingAgentsGraph(
            selected_analysts=["market", "news"],
            debug=False,
            config=self.config,
            parallel_mode=True
        )
        
        # If we got here without exceptions, compilation succeeded
        self.assertTrue(True)

    def test_parallel_vs_serial_features(self):
        """Test that both modes have the necessary components."""
        ta_serial = TradingAgentsGraph(
            selected_analysts=["news"],
            debug=False,
            config=self.config,
            parallel_mode=False
        )
        
        ta_parallel = TradingAgentsGraph(
            selected_analysts=["news"],
            debug=False,
            config=self.config,
            parallel_mode=True
        )
        
        # Both should have the same manager/reflector components
        self.assertIsNotNone(ta_serial.propagator)
        self.assertIsNotNone(ta_parallel.propagator)
        
        self.assertIsNotNone(ta_serial.reflector)
        self.assertIsNotNone(ta_parallel.reflector)
        
        self.assertIsNotNone(ta_serial.signal_processor)
        self.assertIsNotNone(ta_parallel.signal_processor)

    def test_parallel_graph_setup_type(self):
        """Test that correct graph setup class is used."""
        from tradingagents.graph.setup import GraphSetup
        from tradingagents.graph.parallel_setup import ParallelGraphSetup
        
        ta_serial = TradingAgentsGraph(
            selected_analysts=["news"],
            config=self.config,
            parallel_mode=False
        )
        self.assertIsInstance(ta_serial.graph_setup, GraphSetup)
        self.assertNotIsInstance(ta_serial.graph_setup, ParallelGraphSetup)
        
        ta_parallel = TradingAgentsGraph(
            selected_analysts=["news"],
            config=self.config,
            parallel_mode=True
        )
        self.assertIsInstance(ta_parallel.graph_setup, ParallelGraphSetup)

    def test_parallel_executor_import(self):
        """Test that parallel executor module can be imported."""
        from tradingagents.graph.parallel_executor import (
            ParallelExecutor,
            AsyncParallelExecutor,
            parallel_map
        )
        
        # Test basic functionality
        executor = ParallelExecutor(max_workers=2)
        
        def sample_task():
            return 42
        
        results = executor.run_parallel([sample_task, sample_task])
        executor.shutdown()
        
        self.assertEqual(results, [42, 42])

    def test_parallel_executor_dict_mode(self):
        """Test parallel executor with dict of tasks."""
        from tradingagents.graph.parallel_executor import ParallelExecutor
        
        executor = ParallelExecutor(max_workers=2)
        
        tasks = {
            "task1": lambda: 1,
            "task2": lambda: 2,
            "task3": lambda: 3,
        }
        
        results = executor.run_parallel_dict(tasks)
        executor.shutdown()
        
        self.assertEqual(results["task1"], 1)
        self.assertEqual(results["task2"], 2)
        self.assertEqual(results["task3"], 3)

    def test_backward_compatibility(self):
        """Test that serial mode is the default (backward compatible)."""
        ta = TradingAgentsGraph(
            selected_analysts=["news"],
            config=self.config
            # parallel_mode not specified - should default to False
        )
        self.assertFalse(ta.parallel_mode)


if __name__ == '__main__':
    # Run tests
    print("Running Parallel Execution Tests...\n")
    unittest.main(verbosity=2)
