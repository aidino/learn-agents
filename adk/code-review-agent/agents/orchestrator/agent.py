import logging
from typing import Optional
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# Import GitOperationsAgent từ tools module
from ...tools import GitOperationsAgent

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.0-flash-001'

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback that logs when the agent starts processing a request.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    # Get the session state
    state = callback_context.state

    # Set agent name if not present
    if "user_task" not in state:
        state["user_task"] = ""

    # Initialize request counter
    if "pr_link" not in state:
        state["pr_link"] = ""
    
    if "repo_link" not in state:
        state["repo_link"] = ""

    return None

root_agent = Agent(
    model=GEMINI_MODEL,
    name='root_agent',
    description='Bạn là một Agent có chức năng điềù phối hoạt động của hệ thống Code Review',
    instruction="""
    Bạn là một Agent có chức năng điềù phối hoạt động của hệ thống Code Review
    Bạn có thể sử dụng các Agent khác và các tools để hoàn thành các nhiệm vụ của mình.
    
    Nhiệm vụ của bạn:
    - Collect toàn nhưng thông tin cần thiết từ phía người dùng để hệ thống có thể hoạt động, các thông tin cần thiết bao gồm:
        + Nhiệm vụ mà người dùng muốn làm:
        {user_task}
        Hệ thống sẽ chỉ hỗ trợ 2 tasks là: Review PR (Pull request) và review toàn bộ source code.
        Nếu người dùng yêu cầu khác 2 nhiệm vụ này thì bạn cần phải từ chối và giải thích cho người dùng.
        
        + Nếu task là Review PR thì bạn cần phải collect thông tin sau:
            - Link PR: {pr_link}
        
        + Nếu task là review toàn bộ source code thì bạn cần phải collect thông tin sau:
            - Link repo: {repo_link}
        
    - Sau khi đã collect đủ thông tin, bạn cần phải hiển thị toàn bộ thông tin đó cho người dùng để confirm.
            
    """,
    before_agent_callback=before_agent_callback,
    )
