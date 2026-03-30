"""Parallel graph setup with isolated analyst execution.

This implementation keeps analyst tool-calling workflows isolated from each other
by running each analyst in its own subgraph and merging only final reports.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import logging
import time
from typing import Dict, Any, List, Callable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic
from .context_merger import create_context_merge_node


logger = logging.getLogger(__name__)


class ParallelGraphSetup:
    """Setup for partial parallel execution of trading agents graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.max_parallel_workers = 4
        self.global_context_node = create_context_merge_node()

    def _build_single_analyst_graph(
        self,
        analyst_type: str,
        analyst_node: Callable,
        tool_node: ToolNode,
        clear_node: Callable,
    ):
        """Build an isolated subgraph for one analyst tool loop."""
        workflow = StateGraph(AgentState)

        workflow.add_node("Analyst", analyst_node)
        workflow.add_node("Tools", tool_node)
        workflow.add_node("Msg Clear", clear_node)

        workflow.add_edge(START, "Analyst")
        global_router = getattr(self.conditional_logic, f"should_continue_{analyst_type}")

        def local_router(state: AgentState) -> str:
            """Translate global route labels to local subgraph node names."""
            route = global_router(state)
            if isinstance(route, str) and route.startswith("tools_"):
                return "Tools"
            return "Msg Clear"

        workflow.add_conditional_edges(
            "Analyst",
            local_router,
            ["Tools", "Msg Clear"],
        )
        workflow.add_edge("Tools", "Analyst")
        workflow.add_edge("Msg Clear", END)

        return workflow.compile()

    def _create_parallel_analysts_node(
        self,
        selected_analysts: List[str],
        analyst_graphs: Dict[str, Any],
    ):
        """Create one node that runs isolated analyst subgraphs concurrently."""

        report_field_map = {
            "market": "market_report",
            "social": "sentiment_report",
            "news": "news_report",
            "quant": "quant_strategy_report",
            "fundamentals": "fundamentals_report",
        }

        def run_parallel_analysts(state: AgentState) -> Dict[str, Any]:
            outputs: Dict[str, Any] = {}
            workers = min(len(selected_analysts), self.max_parallel_workers)
            phase_start = time.perf_counter()

            if len(selected_analysts) <= 2:
                logger.info(
                    "Parallel analysts enabled with %s analysts. Potential speedup may be limited.",
                    len(selected_analysts),
                )

            def run_single(analyst_key: str) -> Dict[str, Any]:
                start = time.perf_counter()
                local_state = deepcopy(state)
                result = analyst_graphs[analyst_key].invoke(
                    local_state,
                    config={"recursion_limit": 100},
                )
                field = report_field_map[analyst_key]
                elapsed = time.perf_counter() - start
                logger.info("Parallel analyst '%s' finished in %.2fs", analyst_key, elapsed)
                return {field: result.get(field, "")}

            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(run_single, analyst): analyst
                    for analyst in selected_analysts
                }
                for future in as_completed(future_map):
                    outputs.update(future.result())

            phase_elapsed = time.perf_counter() - phase_start
            logger.info(
                "Parallel analysts phase finished in %.2fs (workers=%s, analysts=%s)",
                phase_elapsed,
                workers,
                len(selected_analysts),
            )

            # Keep message history stable for downstream nodes.
            outputs["messages"] = state["messages"]
            return outputs

        return run_parallel_analysts

    def _normalize_selected_analysts(self, selected_analysts: List[str]) -> List[str]:
        """Keep only analysts used by the simplified architecture."""
        allowed = [a for a in selected_analysts if a in ("market", "news", "quant")]
        if not allowed:
            raise ValueError(
                "Trading Agents Graph Setup Error: simplified architecture requires at least one of ['market', 'news', 'quant']."
            )
        return allowed

    def _context_merge_node(self, state: AgentState) -> Dict[str, Any]:
        """Merge analyst reports and refresh global portfolio context."""
        enriched_state = self.global_context_node(state)
        merged_context = (
            f"Market Report:\n{enriched_state.get('market_report', '')}\n\n"
            f"News Report:\n{enriched_state.get('news_report', '')}\n\n"
            f"Quant Strategy Signal Report:\n{enriched_state.get('quant_strategy_report', '')}"
        )
        return {
            "investment_plan": merged_context,
            "global_portfolio_context": enriched_state.get("global_portfolio_context", ""),
            "portfolio_balance": enriched_state.get("portfolio_balance", state.get("portfolio_balance", {})),
        }

    def setup_graph(self, selected_analysts=["market", "news", "quant"]):
        """Set up and compile the agent workflow graph with parallel execution.

        Args:
            selected_analysts (list): List of analyst types to include
        """
        selected_analysts = self._normalize_selected_analysts(selected_analysts)

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "quant" in selected_analysts:
            analyst_nodes["quant"] = create_quant_signal_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["quant"] = create_msg_delete()
            tool_nodes["quant"] = self.tool_nodes["quant"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        chief_trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)
        risk_engine_node = create_risk_engine()

        # Build isolated analyst subgraphs.
        analyst_graphs = {}
        for analyst in selected_analysts:
            analyst_graphs[analyst] = self._build_single_analyst_graph(
                analyst,
                analyst_nodes[analyst],
                tool_nodes[analyst],
                delete_nodes[analyst],
            )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Phase 1: Run analysts concurrently in isolated subgraphs.
        workflow.add_node(
            "Parallel Analysts",
            self._create_parallel_analysts_node(selected_analysts, analyst_graphs),
        )
        workflow.add_node("Context Merge", self._context_merge_node)

        # Remaining phases use stable serial flow.
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Chief Trader", chief_trader_node)
        workflow.add_node("Risk Engine", risk_engine_node)

        workflow.add_edge(START, "Parallel Analysts")
        workflow.add_edge("Parallel Analysts", "Context Merge")
        workflow.add_edge("Context Merge", "Bull Researcher")

        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Chief Trader",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Chief Trader",
            },
        )
        workflow.add_edge("Chief Trader", "Risk Engine")
        workflow.add_edge("Risk Engine", END)

        return workflow.compile()
