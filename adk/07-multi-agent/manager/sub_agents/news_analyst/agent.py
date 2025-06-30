from google.adk.agents import Agent
from google.adk.tools import google_search
from datetime import datetime

def get_current_time():
    """Returns the current time in a specific format."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

news_analyst = Agent(
    name="news_analyst",
    model="gemini-2.0-flash",
    description="News analyst agent",
    instruction="""
        You are a news analyst.
        Use the google_search tool to find the latest news on a given topic.
        Use the get_current_time tool to get the current time and add it to your search query to ensure the news is the latest.
        Summarize the news you find and provide a link to the source.
    """,
    tools=[google_search, get_current_time],
)
