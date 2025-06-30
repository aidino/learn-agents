from google.adk.agents import Agent
import yfinance as yf
from datetime import datetime

def get_stock_price(ticker: str) -> dict:
    """Retrieves current stock price and saves to session state."""
    print(f"--- Tool: get_stock_price called for {ticker} ---")

    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        current_price = stock.info.get("currentPrice")

        if current_price is None:
            return {
                "status": "error",
                "error_message": f"Could not fetch price for {ticker}",
            }

        # Get current timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "success",
            "ticker": ticker,
            "price": current_price,
            "timestamp": current_time,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching stock data: {str(e)}",
        }

stock_analyst = Agent(
    model='gemini-2.0-flash',
    name='stock_analyst',
    description='An agent that can get the latest stock price for a given ticker.',
    instruction="""Get the latest stock price for a given ticker.
You have access to the `get_stock_price` tool to get the latest stock price.
When you have the price, respond in the following format:
<TICKER>: $<PRICE> (updated at <TIMESTAMP>)
For example: GOOG: $175.34 (updated at 2024-04-21 16:30:00)
If the tool fails to get the stock price, please inform the user with a simple explanation of the error.""",
    tools=[get_stock_price],
)