"""
Real-time progress tracking for trading agents.
Displays agent prompts, outputs, and execution progress.
"""

import logging
import json
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
from langchain_core.callbacks import BaseCallbackHandler

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
        self.log_file_path: Optional[str] = None

    def start_run(self, log_file_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start a new run-level JSONL log file and reset in-memory counters."""
        self.node_history = []
        self.llm_calls = []
        self.log_file_path = log_file_path

        path = Path(log_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        header = {
            "event": "run_started",
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._write_jsonl_event(header)

        if self.verbose:
            print(f"📁 Full trace log: {path.as_posix()}")

    def _write_jsonl_event(self, event: Dict[str, Any]) -> None:
        """Append a JSON line event when file logging is enabled."""
        if not self.log_file_path:
            return

        path = Path(self.log_file_path)
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(self._to_jsonable(event), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to write progress log event: %s", exc)

    def _to_jsonable(self, value: Any) -> Any:
        """Best-effort conversion for non-JSON-serializable objects."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): self._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._to_jsonable(v) for v in value]

        # Common LangChain message objects
        content = getattr(value, "content", None)
        msg_type = getattr(value, "type", None)
        tool_calls = getattr(value, "tool_calls", None)
        if content is not None or msg_type is not None or tool_calls is not None:
            return {
                "type": msg_type,
                "content": self._to_jsonable(content),
                "tool_calls": self._to_jsonable(tool_calls),
            }

        # DataFrame or other objects: string fallback
        return str(value)
        
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

        self._write_jsonl_event({
            "event": "node_start",
            "timestamp": timestamp,
            "node_name": node_name,
            "node_type": node_type.value,
            "input_state": state,
        })
        
        if self.verbose:
            self._print_node_start(node_name, node_type, timestamp, state)
    
    def track_node_end(self, node_name: str, output: Any) -> None:
        """
        Track the end of a node execution.
        
        Args:
            node_name: Name of the node that finished
            output: The output produced by the node
        """
        import time
        
        # Find the matching node in history
        node_duration = None
        for node in reversed(self.node_history):
            if node["name"] == node_name and "end_time" not in node:
                node["end_time"] = time.time()
                node["duration"] = node["end_time"] - node["start_time"]
                node_duration = node["duration"]
                break

        self._write_jsonl_event({
            "event": "node_end",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "node_name": node_name,
            "duration": node_duration,
            "output": output,
        })
        
        if self.verbose:
            self._print_node_end(node_name, output)
    
    def track_llm_call(self, 
                      analyst_name: str, 
                      prompt: str, 
                      response: str,
                      duration: float,
                      tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
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
            "tool_calls": tool_calls or [],
        })

        self._write_jsonl_event({
            "event": "llm_call",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analyst": analyst_name,
            "prompt": prompt,
            "response": response,
            "duration": duration,
            "tool_calls": tool_calls or [],
        })
        
        if self.verbose:
            self._print_llm_call(analyst_name, prompt, response, duration)

    def track_tool_event(self, event_name: str, tool_name: str, payload: Any) -> None:
        """Track tool start/end events for real-time UI consumption."""
        self._write_jsonl_event(
            {
                "event": event_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "payload": payload,
            }
        )

    def track_llm_token(self, analyst_name: str, token: str) -> None:
        """Track incremental streamed LLM tokens."""
        self._write_jsonl_event(
            {
                "event": "llm_token",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "analyst": analyst_name,
                "token": token,
            }
        )
    
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

        self._write_jsonl_event({
            "event": "summary",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_execution_time": total_time,
            "total_llm_calls": len(self.llm_calls),
            "time_by_type": by_type,
            "slowest_nodes": [
                {"name": node["name"], "duration": node.get("duration", 0)}
                for node in slow_nodes
            ],
        })
    
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
    
    def _print_node_start(self, node_name: str, node_type: NodeType, timestamp: str, state: Optional[Dict[str, Any]] = None) -> None:
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

        if not isinstance(state, dict):
            return

        input_fields = []
        if state.get("company_of_interest"):
            input_fields.append(f"pair={state.get('company_of_interest')}")
        if state.get("trade_date"):
            input_fields.append(f"date={state.get('trade_date')}")
        if "messages" in state and isinstance(state.get("messages"), list):
            input_fields.append(f"messages={len(state.get('messages'))}")
        if state.get("sender"):
            input_fields.append(f"sender={state.get('sender')}")

        if input_fields:
            print(f"   INPUT: {', '.join(input_fields)}")
    
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

        if isinstance(output, dict):
            output_keys = [
                k for k in [
                    "market_report",
                    "news_report",
                    "quant_strategy_report",
                    "investment_plan",
                    "trader_investment_plan",
                    "final_trade_decision",
                    "risk_debate_state",
                    "investment_debate_state",
                ]
                if k in output and output.get(k)
            ]
            if output_keys:
                print(f"   OUTPUT KEYS: {', '.join(output_keys)}")

            messages = output.get("messages")
            if isinstance(messages, list) and messages:
                last_msg = messages[-1]
                content = getattr(last_msg, "content", None)
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)
                if content:
                    preview = str(content).replace("\n", " ")
                    if len(preview) > 220:
                        preview = preview[:220] + "..."
                    print(f"   OUTPUT MSG: {preview}")
    
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


class LangChainProgressCallback(BaseCallbackHandler):
    """LangChain callback handler for tracking LLM events."""
    
    def __init__(self, progress_tracker: ProgressTracker):
        """
        Initialize callback handler.
        
        Args:
            progress_tracker: The ProgressTracker instance to update
        """
        self.progress_tracker = progress_tracker
        self.current_prompt: Optional[str] = None
        self.start_time: Optional[float] = None
        self._lock = threading.Lock()
        self._run_prompts: Dict[str, str] = {}
        self._run_start_times: Dict[str, float] = {}
        self._run_actors: Dict[str, str] = {}

    def _extract_run_key(self, kwargs: Dict[str, Any]) -> Optional[str]:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return None
        try:
            return str(run_id)
        except Exception:
            return None

    def _resolve_actor_name(self, kwargs, fallback_prompt: Optional[str] = None) -> str:
        """Infer actor name from callback context and prompt content."""
        run_key = self._extract_run_key(kwargs)
        if run_key:
            with self._lock:
                cached_actor = self._run_actors.get(run_key)
            if cached_actor:
                return cached_actor

        explicit_name = kwargs.get("name")
        if explicit_name and explicit_name != "Unknown":
            return str(explicit_name)

        run_name = kwargs.get("run_name")
        if run_name:
            return str(run_name)

        prompt_text = (fallback_prompt or self.current_prompt or "").lower()
        mappings = [
            ("quantitative strategy signal analyst", "Quant Analyst"),
            ("crypto news analyst", "News Analyst"),
            ("crypto market analyst", "Market Analyst"),
            ("bull researcher", "Bull Researcher"),
            ("bear researcher", "Bear Researcher"),
            ("risk management", "Risk Engine"),
            ("trader", "Trader"),
        ]
        for key, label in mappings:
            if key in prompt_text:
                if run_key:
                    with self._lock:
                        self._run_actors[run_key] = label
                return label

        return "Unknown"
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called at the start of LLM execution."""
        import time
        started_at = time.time()
        prompt_text = prompts[0] if prompts else None
        self.start_time = started_at
        self.current_prompt = prompt_text

        run_key = self._extract_run_key(kwargs)
        if run_key:
            with self._lock:
                self._run_start_times[run_key] = started_at
                if prompt_text:
                    self._run_prompts[run_key] = prompt_text

            if prompt_text:
                self._resolve_actor_name(kwargs, fallback_prompt=prompt_text)

    def on_chat_model_start(self, serialized, messages, **kwargs):
        """Called at the start of chat model execution."""
        import time
        started_at = time.time()
        self.start_time = started_at
        prompt_text: Optional[str] = None
        try:
            if messages and messages[0]:
                chunks = []
                for m in messages[0]:
                    role = getattr(m, "type", "message")
                    content = getattr(m, "content", "")
                    if isinstance(content, list):
                        content = " ".join(str(item) for item in content)
                    chunks.append(f"[{role}] {content}")
                prompt_text = "\n".join(chunks)
                self.current_prompt = prompt_text
        except Exception:
            self.current_prompt = None

        run_key = self._extract_run_key(kwargs)
        if run_key:
            with self._lock:
                self._run_start_times[run_key] = started_at
                if prompt_text:
                    self._run_prompts[run_key] = prompt_text

            if prompt_text:
                self._resolve_actor_name(kwargs, fallback_prompt=prompt_text)
    
    def on_llm_end(self, response, **kwargs):
        """Called at the end of LLM execution."""
        import time
        run_key = self._extract_run_key(kwargs)

        prompt_for_run: Optional[str] = None
        start_time_for_run: Optional[float] = self.start_time
        if run_key:
            with self._lock:
                prompt_for_run = self._run_prompts.get(run_key)
                start_time_for_run = self._run_start_times.get(run_key, start_time_for_run)

        duration = time.time() - start_time_for_run if start_time_for_run else 0
        
        # Extract response text
        response_text = ""
        collected_tool_calls: List[Dict[str, Any]] = []
        if hasattr(response, "generations") and response.generations:
            for generation in response.generations:
                candidate = generation[0] if generation else None
                if candidate is None:
                    continue
                if hasattr(candidate, "text") and candidate.text:
                    response_text += str(candidate.text)
                elif hasattr(candidate, "message"):
                    msg = candidate.message
                    content = getattr(msg, "content", "")
                    if isinstance(content, list):
                        content = " ".join(str(item) for item in content)
                    response_text += str(content)

                    msg_tool_calls = getattr(msg, "tool_calls", None)
                    if isinstance(msg_tool_calls, list):
                        for call in msg_tool_calls:
                            if isinstance(call, dict):
                                collected_tool_calls.append(self.progress_tracker._to_jsonable(call))
        
        effective_prompt = prompt_for_run or self.current_prompt
        if effective_prompt and response_text:
            analyst_name = self._resolve_actor_name(kwargs, fallback_prompt=effective_prompt)
            self.progress_tracker.track_llm_call(
                analyst_name,
                effective_prompt,
                response_text,
                duration,
                tool_calls=collected_tool_calls,
            )

        if run_key:
            with self._lock:
                self._run_prompts.pop(run_key, None)
                self._run_start_times.pop(run_key, None)
                self._run_actors.pop(run_key, None)

    def on_llm_new_token(self, token: str, **kwargs):
        """Called for each streamed LLM token when streaming is enabled."""
        if not token:
            return
        analyst_name = self._resolve_actor_name(kwargs)
        self.progress_tracker.track_llm_token(analyst_name, token)

    def on_tool_start(self, serialized, input_str, **kwargs):
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown_tool") if isinstance(serialized, dict) else "unknown_tool"
        self.progress_tracker.track_tool_event("tool_start", str(tool_name), input_str)

    def on_tool_end(self, output, **kwargs):
        """Called when a tool ends."""
        tool_name = kwargs.get("name") or kwargs.get("run_name") or "unknown_tool"
        self.progress_tracker.track_tool_event("tool_end", str(tool_name), output)
    
    def on_llm_error(self, error, **kwargs):
        """Called if LLM execution errors."""
        run_key = self._extract_run_key(kwargs)
        if run_key:
            with self._lock:
                self._run_prompts.pop(run_key, None)
                self._run_start_times.pop(run_key, None)
                self._run_actors.pop(run_key, None)
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
