import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state.get("investment_plan", "")
        debate_history = state.get("investment_debate_state", {}).get("history", "")
        portfolio_balance = state.get("portfolio_balance", {})
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"You are the Chief Trader and portfolio manager for {company_name}. Use the merged analyst context, bull/bear debate transcript, and portfolio constraints to produce a trade intent.\n\nMerged Analyst Context:\n{investment_plan}\n\nBull/Bear Debate Transcript:\n{debate_history}\n\nPortfolio Balance:\n{json.dumps(portfolio_balance, ensure_ascii=False)}\n\nReturn ONLY JSON with this schema:\n{{\n  \"action\": \"BUY\" | \"SELL\" | \"HOLD\",\n  \"confidence\": 0.0-1.0,\n  \"thesis\": \"short explanation\",\n  \"time_horizon\": \"intraday|swing|position\"\n}}",
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are the Chief Trader. Produce strict JSON only (no markdown, no prose outside JSON). Use BUY/SELL/HOLD for action and include confidence between 0 and 1. Leverage these past lessons: {past_memory_str}""",
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
