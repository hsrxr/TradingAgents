import os

DEFAULT_CONFIG = {
    # Paths
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),

    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",

    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "llm_timeout_seconds": 180.0,
    "llm_max_retries": 5,

    # Debate and discussion settings
    "max_debate_rounds": 1,
    # Kept for compatibility with existing CLI wiring.
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "graph_invoke_retries": 3,
    "graph_invoke_backoff_seconds": 2.0,

    # Deterministic risk-engine settings
    "max_position_pct": 0.20,
    "max_single_order_pct": 0.10,

    # Progress tracking settings
    "enable_progress_tracking": True,   # Enable real-time progress display
    "enable_colored_output": True,      # Use colored output for better readability
}
