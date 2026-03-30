import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state.get("investment_plan", "")
        debate_history = state.get("investment_debate_state", {}).get("history", "")
        portfolio_balance = state.get("portfolio_balance", {})
        global_portfolio_context = state.get("global_portfolio_context", "Portfolio context unavailable.")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        quant_strategy_report = state.get("quant_strategy_report", "")
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{quant_strategy_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=3)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"You are the Chief Trader and portfolio manager for {company_name} in the crypto market. Use the merged analyst context, bull/bear debate transcript, and portfolio constraints to produce a **hourly trade intent** for the next 6-24h.\n\nDecision rules:\n- Prioritize executable short-horizon setups over long-term narratives.\n- If signal quality is weak or conflicting, choose HOLD with clear reasoning.\n- Confidence must reflect signal quality and consistency across market/news/sentiment/fundamentals.\n\nMerged Analyst Context:\n{investment_plan}\n\nBull/Bear Debate Transcript:\n{debate_history}\n\nGlobal Portfolio Context (hard constraints):\n{global_portfolio_context}\n\nPortfolio Balance:\n{json.dumps(portfolio_balance, ensure_ascii=False)}\n\nReturn ONLY JSON with this schema:\n{{\n  \"action\": \"BUY\" | \"SELL\" | \"HOLD\",\n  \"confidence\": 0.0-1.0,\n  \"thesis\": \"short explanation for next 6-24h\",\n  \"time_horizon\": \"intraday|swing|position\"\n}}\n\nFor this strategy, default to \"intraday\" unless strong evidence supports a longer horizon.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are the Chief Trader for a crypto, hourly-frequency strategy. Produce strict JSON only (no markdown, no prose outside JSON).
Requirements:
- action must be exactly BUY, SELL, or HOLD.
- confidence must be a float between 0 and 1.
- thesis must be concise and focused on the next 6-24h.
- Prefer time_horizon='intraday' for this strategy unless there is strong cross-signal confirmation for longer duration.
Leverage these past lessons: {past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
