from google.adk.agents import Agent
from .sub_agents.news_analyst import news_analyst
from .sub_agents.stock_analyst import stock_analyst

root_agent = Agent(
    model='gemini-2.0-flash',
    name='root_agent',
    description='A helpful assistant for user questions about companies and stocks.',
    instruction="""You are a financial assistant that coordinates with specialist agents.

When a user asks about a company's stock, you must:
1. First transfer to the stock_analyst to get the latest stock price for the company's ticker
2. Then transfer to the news_analyst to find recent news about the company  
3. Finally, combine both results into a comprehensive response for the user

Always start by presenting the stock information clearly, then provide a summary of the recent news to give context about the company's situation.

You can transfer to other agents using the transfer_to_agent function when needed.""",
    sub_agents=[stock_analyst, news_analyst],
)


