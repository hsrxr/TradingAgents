from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.dataflows.rss_processor import fetch_and_parse_crypto_news
from tradingagents.dataflows.get_full_articles import fetch_article_full_text
from tradingagents.triggers.observers import fetch_trigger_watch_news

def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            fetch_trigger_watch_news,
            fetch_and_parse_crypto_news,
            fetch_article_full_text,
        ]

        # system_message = (
        #     "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news, and fetch_and_parse_crypto_news(limit) for the latest cryptocurrency news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
        #     + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
        # )
        # Given the limitations of the context window, we recommend that you do not select more than three articles to view in full at any one time.
        system_message = (
            "You are a crypto news analyst focused on **hourly trading impact** (next 6-24 hours)."
            " Your analysis scope must include both:"
            " (1) SEC press releases + watched X accounts via fetch_trigger_watch_news(limit), and"
            " (2) broader crypto RSS via fetch_and_parse_crypto_news(limit)."
            " First call fetch_trigger_watch_news(limit), then fetch_and_parse_crypto_news(limit), merge both feeds, rank by near-term tradability, then call fetch_article_full_text only for the highest-impact items."
            " Keep article selection disciplined (prefer depth on a few high-impact stories over shallow coverage on many stories)."
            " Prioritize catalysts such as exchange listings/delistings, exploits/hacks, regulation headlines, ETF/fund flow headlines, protocol/governance changes, token unlocks, and macro surprises that affect crypto beta."
            " For each selected story, explain expected direction, likely time-to-impact, affected assets, and whether impact is likely one-shot or persistent."
            " Avoid generic language like 'market sentiment is mixed' without concrete implications."
            + """ Make sure to append a Markdown table at the end with columns: headline, catalyst type, affected assets, expected 6-24h impact, confidence, and invalidation/watch items."""
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. We are analyzing crypto asset/pair {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
