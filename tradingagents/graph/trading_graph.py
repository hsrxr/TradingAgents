# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
import logging
import time
import datetime
from datetime import date
from typing import Dict, Any, Tuple, List, Optional
from langgraph.prebuilt import ToolNode
from tradingagents.llm_clients import create_llm_client

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

# Import direct DEX tools from dataflow layer
from tradingagents.dataflows.geckoterminal_price import get_dex_ohlcv
from tradingagents.dataflows.calculate_indicators import get_dex_indicators
from tradingagents.dataflows.rss_processor import fetch_and_parse_crypto_news
from tradingagents.dataflows.get_full_articles import fetch_article_full_text

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .parallel_setup import ParallelGraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor
from .progress_tracker import ProgressTracker, LangChainProgressCallback


logger = logging.getLogger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "news"],
        debug=False,
        config: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None,
        parallel_mode: bool = False,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
            parallel_mode: If True, enables parallel execution of analysts, debates, and risk analysis.
                          If False, uses serial execution (default behavior).
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []
        self.parallel_mode = parallel_mode
        self.selected_analysts = selected_analysts

        if self.parallel_mode and len(selected_analysts) <= 2:
            logger.info(
                "parallel_mode=True with %s analysts. Overhead/retries may outweigh speedup.",
                len(selected_analysts),
            )

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs with provider-specific thinking configuration
        llm_kwargs = self._get_provider_kwargs()

        # Progress tracking
        self.progress_tracker = ProgressTracker(
            verbose=self.config.get("enable_progress_tracking", True),
            enable_colors=self.config.get("enable_colored_output", True)
        )
        self.progress_callback = LangChainProgressCallback(self.progress_tracker)

        # Add callbacks to kwargs (internal progress callback + optional external callbacks)
        llm_callbacks = [self.progress_callback]
        if self.callbacks:
            llm_callbacks.extend(self.callbacks)
        llm_kwargs["callbacks"] = llm_callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()
        
        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        
        # Choose between parallel and serial graph setup
        if self.parallel_mode:
            self.graph_setup = ParallelGraphSetup(
                self.quick_thinking_llm,
                self.deep_thinking_llm,
                self.tool_nodes,
                self.bull_memory,
                self.bear_memory,
                self.trader_memory,
                self.invest_judge_memory,
                self.risk_manager_memory,
                self.conditional_logic,
            )
        else:
            self.graph_setup = GraphSetup(
                self.quick_thinking_llm,
                self.deep_thinking_llm,
                self.tool_nodes,
                self.bull_memory,
                self.bear_memory,
                self.trader_memory,
                self.invest_judge_memory,
                self.risk_manager_memory,
                self.conditional_logic,
            )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the primary graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

        # Keep a serial graph as fallback when parallel mode hits provider/tool-message constraints.
        self.serial_graph = None
        if self.parallel_mode:
            serial_setup = GraphSetup(
                self.quick_thinking_llm,
                self.deep_thinking_llm,
                self.tool_nodes,
                self.bull_memory,
                self.bear_memory,
                self.trader_memory,
                self.invest_judge_memory,
                self.risk_manager_memory,
                self.conditional_logic,
            )
            self.serial_graph = serial_setup.setup_graph(selected_analysts)

    def _invoke_graph(self, graph, init_agent_state, args):
        """Invoke a graph in debug or normal mode and return final state."""
        if self.debug or self.config.get("enable_progress_tracking", True):
            trace = []
            for idx, chunk in enumerate(graph.stream(init_agent_state, **args), start=1):
                step_name = f"Graph Step {idx}"
                self.progress_tracker.track_node_start(step_name, chunk)

                messages = chunk.get("messages", []) if isinstance(chunk, dict) else []
                if self.debug and messages:
                    messages[-1].pretty_print()

                self.progress_tracker.track_node_end(step_name, chunk)
                trace.append(chunk)

            if not trace:
                raise RuntimeError("Graph stream produced no chunks.")
            return trace[-1]

        return graph.invoke(init_agent_state, **args)

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        llm_timeout = self.config.get("llm_timeout_seconds")
        if llm_timeout is not None:
            kwargs["timeout"] = llm_timeout

        llm_max_retries = self.config.get("llm_max_retries")
        if llm_max_retries is not None:
            kwargs["max_retries"] = llm_max_retries

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        return kwargs

    def _is_tool_call_sequence_error(self, exc: Exception) -> bool:
        """Detect provider errors caused by mismatched tool-call message sequences."""
        error_text = str(exc)
        return "tool_calls" in error_text and "tool_call_id" in error_text

    def _is_transient_connection_error(self, exc: Exception) -> bool:
        """Detect transient transport/API failures that should be retried."""
        error_text = str(exc).lower()
        transient_markers = (
            "connection error",
            "remoteprotocolerror",
            "incomplete chunked read",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "service unavailable",
            "502",
            "503",
            "504",
        )
        return any(marker in error_text for marker in transient_markers)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Decentralized exchange data
                    get_dex_ohlcv,
                    get_dex_indicators,                                      
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    # get_news,
                    # get_global_news,
                    # get_insider_transactions,
                    fetch_and_parse_crypto_news,
                    fetch_article_full_text,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name
        args = self.propagator.get_graph_args()

        # Create per-run full trace log file for step-by-step I/O and LLM prompt/response.
        trace_dir = Path(f"eval_results/{company_name}/TradingAgentsStrategy_logs/")
        trace_dir.mkdir(parents=True, exist_ok=True)
        run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_trade_date = str(trade_date).replace(":", "-").replace("/", "-")
        trace_file = trace_dir / f"full_trace_{safe_trade_date}_{run_ts}.jsonl"
        self.progress_tracker.start_run(
            str(trace_file),
            metadata={"company": company_name, "trade_date": str(trade_date), "parallel_mode": self.parallel_mode},
        )

        max_attempts = int(self.config.get("graph_invoke_retries", 3))
        base_backoff = float(self.config.get("graph_invoke_backoff_seconds", 2.0))

        current_graph = self.graph
        used_fallback = False
        final_state = None
        
        # Track overall execution
        self.progress_tracker.track_node_start("Trading Analysis", {"company": company_name, "date": trade_date})
        overall_start_time = time.time()

        for attempt in range(1, max_attempts + 1):
            init_agent_state = self.propagator.create_initial_state(
                company_name, trade_date
            )
            try:
                final_state = self._invoke_graph(current_graph, init_agent_state, args)
                break
            except Exception as exc:
                if (
                    self.parallel_mode
                    and self.serial_graph is not None
                    and not used_fallback
                    and self._is_tool_call_sequence_error(exc)
                ):
                    logger.warning(
                        "Parallel execution failed due to tool-call message sequencing. "
                        "Falling back to serial graph for this run."
                    )
                    self.progress_tracker.track_node_start("Fallback to Serial Execution", {})
                    current_graph = self.serial_graph
                    used_fallback = True
                    continue

                if self._is_transient_connection_error(exc) and attempt < max_attempts:
                    sleep_seconds = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient connection/API error on attempt %s/%s. Retrying in %.1fs. Error: %s",
                        attempt,
                        max_attempts,
                        sleep_seconds,
                        exc,
                    )
                    time.sleep(sleep_seconds)
                    continue

                raise

        if final_state is None:
            raise RuntimeError("Graph execution failed without producing a final state.")

        # Track completion
        overall_duration = time.time() - overall_start_time
        self.progress_tracker.track_node_end("Trading Analysis", {"status": "completed", "duration": overall_duration})
        
        # Print summary only if progress tracking is enabled
        if self.config.get("enable_progress_tracking", True):
            self.progress_tracker.print_summary()

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"])


    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        # Safely build investment_debate_state (may have partial fields in simplified architecture)
        invest_debate_log = {}
        if "investment_debate_state" in final_state:
            invest_debate = final_state["investment_debate_state"]
            invest_debate_log = {
                "bull_history": invest_debate.get("bull_history", ""),
                "bear_history": invest_debate.get("bear_history", ""),
                "history": invest_debate.get("history", ""),
                "current_response": invest_debate.get("current_response", ""),
                "judge_decision": invest_debate.get("judge_decision", ""),
            }
        
        # Safely build risk_debate_state (pure Python risk engine may not populate all fields)
        risk_debate_log = {}
        if "risk_debate_state" in final_state:
            risk_debate = final_state["risk_debate_state"]
            risk_debate_log = {
                "aggressive_history": risk_debate.get("aggressive_history", ""),
                "conservative_history": risk_debate.get("conservative_history", ""),
                "neutral_history": risk_debate.get("neutral_history", ""),
                "history": risk_debate.get("history", ""),
                "judge_decision": risk_debate.get("judge_decision", ""),
            }
        
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state.get("company_of_interest", ""),
            "trade_date": final_state.get("trade_date", ""),
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "fundamentals_report": final_state.get("fundamentals_report", ""),
            "investment_debate_state": invest_debate_log,
            "trader_investment_decision": final_state.get("trader_investment_plan", ""),
            "risk_debate_state": risk_debate_log,
            "investment_plan": final_state.get("investment_plan", ""),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
