"""
Real-time progress tracking for trading agents.
Displays agent prompts, outputs, and execution progress.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

try:
    from colorama import Fore, Back, Style, init
    COLORAMA_AVAILABLE = True
    init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    # Define dummy color constants if colorama is not available
    class DummyColor:
        def __add__(self, other):
            return ""
        def __radd__(self, other):
            return str(other)
        def __str__(self):
            return ""
    
    class DummyColors:
        CYAN = DummyColor()
        YELLOW = DummyColor()
        MAGENTA = DummyColor()
        RED = DummyColor()
        GREEN = DummyColor()
        WHITE = DummyColor()
        BLUE = DummyColor()
        LIGHTBLACK_EX = DummyColor()
        
    Fore = DummyColors()
    Style = DummyColors()
    Style.BRIGHT = ""
    Style.RESET_ALL = ""

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enum for different node types in the graph."""
    ANALYST = "analyst"
    TOOL = "tool"
    DEBATE = "debate"
    RISK = "risk_management"
    TRADER = "trader"
    OTHER = "other"


class ProgressTracker:
    """Tracks and displays real-time progress of agent execution."""

    def __init__(self, verbose: bool = True, enable_colors: bool = True):
        """
        Initialize progress tracker.
        
        Args:
            verbose: If True, print detailed progress information
            enable_colors: If True, use colored output with colorama
        """
        self.verbose = verbose
        self.enable_colors = enable_colors
        self.node_history: List[Dict[str, Any]] = []
        self.llm_calls: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.phase_start_times: Dict[str, float] = {}
        
    def track_node_start(self, node_name: str, state: Dict[str, Any]) -> None:
        """
        Track the start of a node execution.
        
        Args:
            node_name: Name of the node being executed
            state: The state passed to the node
        """
        import time
        
        node_type = self._determine_node_type(node_name)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.node_history.append({
            "name": node_name,
            "type": node_type,
            "start_time": time.time(),
            "start_timestamp": timestamp,
            "state_keys": list(state.keys()) if isinstance(state, dict) else [],
        })
        
        if self.verbose:
            self._print_node_start(node_name, node_type, timestamp)
    
    def track_node_end(self, node_name: str, output: Any) -> None:
        """
        Track the end of a node execution.
        
        Args:
            node_name: Name of the node that finished
            output: The output produced by the node
        """
        import time
        
        # Find the matching node in history
        for node in reversed(self.node_history):
            if node["name"] == node_name and "end_time" not in node:
                node["end_time"] = time.time()
                node["duration"] = node["end_time"] - node["start_time"]
                break
        
        if self.verbose:
            self._print_node_end(node_name, output)
    
    def track_llm_call(self, 
                      analyst_name: str, 
                      prompt: str, 
                      response: str,
                      duration: float) -> None:
        """
        Track an LLM call with its prompt and response.
        
        Args:
            analyst_name: Name of the analyst making the call
            prompt: The prompt sent to the LLM
            response: The response from the LLM
            duration: Execution time in seconds
        """
        self.llm_calls.append({
            "analyst": analyst_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prompt": prompt,
            "response": response,
            "duration": duration,
        })
        
        if self.verbose:
            self._print_llm_call(analyst_name, prompt, response, duration)
    
    def track_analyst_report(self, analyst_name: str, report: str, duration: float) -> None:
        """
        Track an analyst's final report.
        
        Args:
            analyst_name: Name of the analyst
            report: The analyst's report
            duration: Time taken to generate report
        """
        if self.verbose:
            self._print_analyst_report(analyst_name, report, duration)
    
    def print_summary(self) -> None:
        """Print execution summary."""
        if not self.verbose:
            return
        
        total_time = sum(
            node.get("duration", 0) 
            for node in self.node_history 
            if "duration" in node
        )
        
        print(f"\n{Style.BRIGHT}{'=' * 80}")
        print(f"EXECUTION SUMMARY")
        print(f"{'=' * 80}{Style.RESET_ALL}")
        
        # Group by node type
        by_type: Dict[str, float] = {}
        for node in self.node_history:
            if "duration" in node:
                node_type = node["type"].value if hasattr(node["type"], "value") else str(node["type"])
                if node_type not in by_type:
                    by_type[node_type] = 0
                by_type[node_type] += node["duration"]
        
        print(f"\nTime by Node Type:")
        for node_type, time_spent in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  {node_type:20} {time_spent:8.2f}s ({time_spent/total_time*100:.1f}%)")
        
        print(f"\nTotal Execution Time: {total_time:.2f}s")
        print(f"Total LLM Calls: {len(self.llm_calls)}")
        
        # Show slowest nodes
        slow_nodes = sorted(
            [n for n in self.node_history if "duration" in n],
            key=lambda x: x["duration"],
            reverse=True
        )[:5]
        
        if slow_nodes:
            print(f"\nSlowest Nodes:")
            for node in slow_nodes:
                print(f"  {node['name']:30} {node['duration']:8.2f}s")
    
    def get_llm_calls_json(self) -> List[Dict[str, Any]]:
        """Get all LLM calls in JSON format for external processing."""
        return self.llm_calls
    
    def _determine_node_type(self, node_name: str) -> NodeType:
        """Determine the type of node based on its name."""
        name_lower = node_name.lower()
        
        if "analyst" in name_lower or any(x in name_lower for x in ["market", "news", "social", "fundamentals"]):
            return NodeType.ANALYST
        elif "tool" in name_lower:
            return NodeType.TOOL
        elif "debate" in name_lower or "invest" in name_lower:
            return NodeType.DEBATE
        elif "risk" in name_lower:
            return NodeType.RISK
        elif "trader" in name_lower:
            return NodeType.TRADER
        else:
            return NodeType.OTHER
    
    def _print_node_start(self, node_name: str, node_type: NodeType, timestamp: str) -> None:
        """Print node start information."""
        node_type_str = node_type.value.upper()
        
        if self.enable_colors:
            color_map = {
                NodeType.ANALYST: Fore.CYAN,
                NodeType.TOOL: Fore.YELLOW,
                NodeType.DEBATE: Fore.MAGENTA,
                NodeType.RISK: Fore.RED,
                NodeType.TRADER: Fore.GREEN,
                NodeType.OTHER: Fore.WHITE,
            }
            color = color_map.get(node_type, Fore.WHITE)
            print(f"\n{color}▶ [{timestamp}] {node_type_str:15} {node_name}{Style.RESET_ALL}")
        else:
            print(f"\n▶ [{timestamp}] {node_type_str:15} {node_name}")
    
    def _print_node_end(self, node_name: str, output: Any) -> None:
        """Print node end information."""
        # Find duration from history
        duration = None
        for node in reversed(self.node_history):
            if node["name"] == node_name:
                duration = node.get("duration")
                break
        
        if self.enable_colors:
            print(f"{Fore.GREEN}✓ {node_name} completed in {duration:.2f}s{Style.RESET_ALL}" if duration else f"{Fore.GREEN}✓ {node_name} completed{Style.RESET_ALL}")
        else:
            print(f"✓ {node_name} completed in {duration:.2f}s" if duration else f"✓ {node_name} completed")
    
    def _print_llm_call(self, analyst_name: str, prompt: str, response: str, duration: float) -> None:
        """Print LLM call information."""
        prompt_preview = prompt[:150].replace("\n", " ") + "..." if len(prompt) > 150 else prompt.replace("\n", " ")
        response_preview = response[:150].replace("\n", " ") + "..." if len(response) > 150 else response.replace("\n", " ")
        
        if self.enable_colors:
            print(f"\n{Fore.BLUE}📝 [{analyst_name}] PROMPT:{Style.RESET_ALL}")
            print(f"   {Fore.LIGHTBLACK_EX}{prompt_preview}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📤 RESPONSE: ({duration:.2f}s){Style.RESET_ALL}")
            print(f"   {Fore.LIGHTBLACK_EX}{response_preview}{Style.RESET_ALL}")
        else:
            print(f"\n📝 [{analyst_name}] PROMPT:")
            print(f"   {prompt_preview}")
            print(f"📤 RESPONSE: ({duration:.2f}s)")
            print(f"   {response_preview}")
    
    def _print_analyst_report(self, analyst_name: str, report: str, duration: float) -> None:
        """Print analyst's report."""
        report_lines = report.split("\n")
        summary = "\n".join(report_lines[:5])  # First 5 lines
        if len(report_lines) > 5:
            summary += f"\n... ({len(report_lines) - 5} more lines)"
        
        if self.enable_colors:
            print(f"\n{Fore.YELLOW}📊 [{analyst_name}] REPORT ({duration:.2f}s):{Style.RESET_ALL}")
            print(f"{Fore.LIGHTBLACK_EX}{summary}{Style.RESET_ALL}")
        else:
            print(f"\n📊 [{analyst_name}] REPORT ({duration:.2f}s):")
            print(f"{summary}")


class LangChainProgressCallback:
    """LangChain callback handler for tracking LLM events."""
    
    def __init__(self, progress_tracker: ProgressTracker):
        """
        Initialize callback handler.
        
        Args:
            progress_tracker: The ProgressTracker instance to update
        """
        self.progress_tracker = progress_tracker
        self.current_prompt = None
        self.start_time = None
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called at the start of LLM execution."""
        import time
        self.start_time = time.time()
        if prompts:
            self.current_prompt = prompts[0]
    
    def on_llm_end(self, response, **kwargs):
        """Called at the end of LLM execution."""
        import time
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Extract response text
        response_text = ""
        if hasattr(response, "generations") and response.generations:
            for generation in response.generations:
                if hasattr(generation[0], "text"):
                    response_text += generation[0].text
        
        if self.current_prompt and response_text:
            analyst_name = kwargs.get("name", "Unknown")
            self.progress_tracker.track_llm_call(
                analyst_name,
                self.current_prompt,
                response_text,
                duration
            )
    
    def on_llm_error(self, error, **kwargs):
        """Called if LLM execution errors."""
        logger.error(f"LLM Error: {error}")


# Convenience function for creating a progress tracker with logging
def setup_progress_tracking(log_level=logging.INFO, verbose=True) -> ProgressTracker:
    """
    Set up progress tracking with proper logging configuration.
    
    Args:
        log_level: Logging level (default: INFO)
        verbose: If True, enable verbose progress output
    
    Returns:
        Configured ProgressTracker instance
    """
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return ProgressTracker(verbose=verbose, enable_colors=True)
