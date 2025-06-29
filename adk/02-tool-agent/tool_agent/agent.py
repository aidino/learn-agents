from google.adk.agents import Agent
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import google_search
from datetime import datetime

def get_current_time() -> dict:
    return {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

root_agent = LlmAgent(
    model=LiteLlm(model="openai/gpt-3.5-turbo"),
    name='tool_agent',
    description='Tool agent.',
    instruction="""
    Bạn là một trợ lý có thể sử dụng tool sau:
    - google_search: Tool tìm kiếm thông tin trên mạng
    - get_current_time: Tool lấy thời gian hiện tại 
    """,
    tools=[google_search, get_current_time]
    # tools=[get_current_time]
)
