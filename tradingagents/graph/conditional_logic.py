# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        # Simplified architecture: hard cap at 2 total turns (Bull + Bear).
        debate_state = state.get("investment_debate_state", {})
        if debate_state.get("count", 0) >= 2:
            return "Research Manager"
        current_response = debate_state.get("current_response", "")
        if current_response.startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"
