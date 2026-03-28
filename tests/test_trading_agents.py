import time
from tradingagents.dataflows.y_finance import get_YFin_data_online, get_stock_stats_indicators_window, get_balance_sheet as get_yfinance_balance_sheet, get_cashflow as get_yfinance_cashflow, get_income_statement as get_yfinance_income_statement, get_insider_transactions as get_yfinance_insider_transactions

# print("Testing optimized implementation with 30-day lookback:")
# start_time = time.time()
# result = get_stock_stats_indicators_window("AAPL", "macd", "2024-11-01", 30)
# end_time = time.time()

# print(f"Execution time: {end_time - start_time:.2f} seconds")
# print(f"Result length: {len(result)} characters")
# print(result)

# ----------------------------------
# import os
# from dotenv import load_dotenv

# load_dotenv()
# print(os.getenv("OPENAI_API_KEY"))

# -----------------------------------
from openai import OpenAI

# for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
client = OpenAI(api_key="sk-dc3769b169f043e9aa17489c376c3d9e", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": ""},
        {"role": "user", "content": "为了防"},
  ],
    max_tokens=1024,
    temperature=0.7,
    stream=True,
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)