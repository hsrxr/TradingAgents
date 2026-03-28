from langchain_core.messages import AIMessage
import time
import json


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

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

        prompt = f"""You are the Bear Researcher for a **crypto market strategy with hourly execution**. Build the strongest evidence-based downside thesis for the next 6-24 hours.

    Your responsibilities:
    - Argue why downside or failed upside follow-through is more probable in the short horizon.
    - Use concrete signals from liquidity/risk-off behavior, momentum deterioration, volatility expansion, weak sentiment, and adverse catalysts.
    - Translate evidence into tradable bearish logic (what price behavior should happen next if the bear case is correct).
    - Directly rebut the latest bull claims and expose optimistic assumptions.

    Quality bar:
    - Be explicit about timing (immediate, next 1-3 candles, next 6-24h).
    - Separate structural weakness from temporary noise.
    - Provide invalidation conditions that would weaken the bear thesis.
    - Avoid vague fear-based language; ground claims in reported evidence.

    Resources available:
    Market research report: {market_research_report}
    Social media sentiment report: {sentiment_report}
    Latest crypto/macro news report: {news_report}
    Fundamentals/on-chain context report: {fundamentals_report}
    Conversation history of the debate: {history}
    Last bull argument: {current_response}
    Reflections from similar situations and lessons learned: {past_memory_str}

    Output format:
    1) Bear thesis summary (2-4 sentences)
    2) Evidence bullets (market, sentiment, news, fundamentals)
    3) Direct rebuttal to bull points
    4) Hourly trade implications (rejection/continuation trigger, downside target idea, invalidation)

    Use this information to deliver a compelling, realistic, short-horizon bear argument. You must also incorporate reflections and lessons learned from past mistakes.
    """

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "judge_decision": investment_debate_state.get("judge_decision", ""),
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
