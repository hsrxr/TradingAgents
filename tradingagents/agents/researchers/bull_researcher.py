from langchain_core.messages import AIMessage
import time
import json


def create_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are the Bull Researcher for a **crypto market strategy with hourly execution**. Build the best evidence-based long thesis for the next 6-24 hours, not a multi-year investment story.

    Your responsibilities:
    - Argue why upside is more probable in the short horizon.
    - Use concrete signals from market structure, momentum, volatility, sentiment, and news catalysts.
    - Convert evidence into tradable logic (what should happen next if the bull case is correct).
    - Directly rebut the latest bear claims and point out weak assumptions.

    Quality bar:
    - Be specific about timing (immediate, next 1-3 candles, next 6-24h).
    - Distinguish catalyst-driven move vs. technical continuation.
    - Mention invalidation conditions that would weaken the bull case.
    - Avoid generic claims without explicit evidence from the provided reports.

    Resources available:
    Market research report: {market_research_report}
    Social media sentiment report: {sentiment_report}
    Latest crypto/macro news report: {news_report}
    Fundamentals/on-chain context report: {fundamentals_report}
    Conversation history of the debate: {history}
    Last bear argument: {current_response}
    Reflections from similar situations and lessons learned: {past_memory_str}

    Output format:
    1) Bull thesis summary (2-4 sentences)
    2) Evidence bullets (market, sentiment, news, fundamentals)
    3) Direct rebuttal to bear points
    4) Hourly trade implications (entry zone idea, continuation trigger, invalidation)

    Use this information to deliver a compelling, realistic, short-horizon bull argument. You must also incorporate reflections and lessons learned from past mistakes.
    """

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "judge_decision": investment_debate_state.get("judge_decision", ""),
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
