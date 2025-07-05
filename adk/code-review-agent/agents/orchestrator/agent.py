import logging
from typing import Optional
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
import re

# Import GitOperationsAgent từ tools module
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from tools.git_operations import GitOperationsAgent

# Import StateManager
from .state_manager import StateManager, log_state_change

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.0-flash-001'

def get_state_dict_safely(state) -> dict:
    """
    Safely convert ADK state object to dictionary.
    
    Args:
        state: ADK state object
        
    Returns:
        Dictionary representation of state
    """
    try:
        # Try to use to_dict() method if available
        if hasattr(state, 'to_dict'):
            return state.to_dict()
        
        # Try to access _value attribute if available
        if hasattr(state, '_value'):
            return dict(state._value)
        
        # Fallback: create dict from state items
        state_dict = {}
        for key in ["user_task", "pr_link", "repo_link", "information_collection_status", "collected_info"]:
            try:
                state_dict[key] = state.get(key, "")
            except:
                state_dict[key] = ""
        
        return state_dict
    except Exception as e:
        logger.warning(f"Could not convert state to dict: {e}")
        return {}

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback được gọi trước khi agent bắt đầu xử lý request.
    Khởi tạo state các thông tin cần thiết nếu chưa có.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    # Get the session state
    state = callback_context.state

    # Khởi tạo các state keys nếu chưa có
    if "user_task" not in state:
        state["user_task"] = ""
    
    if "pr_link" not in state:
        state["pr_link"] = ""
    
    if "repo_link" not in state:
        state["repo_link"] = ""
    
    if "information_collection_status" not in state:
        state["information_collection_status"] = "collecting"  # collecting, collected, confirmed
    
    if "collected_info" not in state:
        state["collected_info"] = {}

    # Log state change safely
    state_dict = get_state_dict_safely(state)
    log_state_change(state_dict, "before_agent_callback", "Initialized state keys")
    
    logger.info(f"Before agent callback - Current state initialized")
    return None

def after_agent_callback(callback_context: CallbackContext, agent_response: types.Content) -> Optional[types.Content]:
    """
    Callback được gọi sau khi agent hoàn thành xử lý.
    Phân tích response và lưu thông tin collect được vào state.

    Args:
        callback_context: Contains state and context information
        agent_response: Response from the agent

    Returns:
        None to continue with normal processing, or modified Content
    """
    try:
        # Get the session state
        state = callback_context.state
        
        # Lấy text response từ agent
        response_text = ""
        if agent_response and agent_response.parts:
            for part in agent_response.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
        
        logger.info(f"After agent callback - Processing response: {response_text[:200]}...")
        
        # Phân tích response để extract thông tin
        extracted_info = extract_information_from_response(response_text)
        
        # Cập nhật state với thông tin extracted
        if extracted_info:
            _update_state_with_extracted_info(state, extracted_info)
            # Log state change safely
            state_dict = get_state_dict_safely(state)
            log_state_change(state_dict, "after_agent_callback", f"Extracted info: {extracted_info}")
        
        # Kiểm tra xem đã collect đủ thông tin chưa
        _check_information_completeness(state)
        
        # Kiểm tra và tạo confirmation message nếu cần
        _generate_confirmation_message_if_needed(state, response_text)
        
        logger.info(f"After agent callback - State updated successfully")
        
    except Exception as e:
        logger.error(f"Error in after_agent_callback: {e}")
    
    return None

def extract_information_from_response(response_text: str) -> dict:
    """
    Phân tích response text để extract thông tin cần thiết.
    
    Args:
        response_text: Text response from agent
        
    Returns:
        Dictionary containing extracted information
    """
    extracted_info = {}
    
    # Patterns để detect các loại thông tin
    patterns = {
        'task_review_pr': r'(?i)(?:review|check|analyze).*(?:pr|pull request)',
        'task_review_code': r'(?i)(?:review|check|analyze).*(?:code|source code|repository)',
        'pr_link': r'(?i)(?:pr|pull request).*(?:link|url).*?(?:https?://[^\s]+)',
        'repo_link': r'(?i)(?:repo|repository).*(?:link|url).*?(?:https?://[^\s]+)',
        'github_pr_link': r'https://github\.com/[^/]+/[^/]+/pull/\d+',
        'github_repo_link': r'https://github\.com/[^/]+/[^/]+(?:\.git)?',
        'user_confirmation': r'(?i)(?:yes|confirm|correct|ok|proceed|đúng|xác nhận)',
    }
    
    # Extract task type
    if re.search(patterns['task_review_pr'], response_text):
        extracted_info['task_type'] = 'review_pr'
    elif re.search(patterns['task_review_code'], response_text):
        extracted_info['task_type'] = 'review_code'
    
    # Extract links
    github_pr_matches = re.findall(patterns['github_pr_link'], response_text)
    if github_pr_matches:
        extracted_info['pr_link'] = github_pr_matches[0]
    
    github_repo_matches = re.findall(patterns['github_repo_link'], response_text)
    if github_repo_matches:
        extracted_info['repo_link'] = github_repo_matches[0]
    
    # Check for user confirmation
    if re.search(patterns['user_confirmation'], response_text):
        extracted_info['user_confirmed'] = True
    
    # Extract từ user input (nếu có trong response)
    lines = response_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('* Task:') or line.startswith('Task:'):
            task_part = line.split(':', 1)[1].strip()
            if 'pr' in task_part.lower() or 'pull request' in task_part.lower():
                extracted_info['task_type'] = 'review_pr'
            elif 'code' in task_part.lower() or 'source' in task_part.lower():
                extracted_info['task_type'] = 'review_code'
        
        elif line.startswith('* PR link:') or line.startswith('PR link:'):
            link_part = line.split(':', 1)[1].strip()
            if 'github.com' in link_part and '/pull/' in link_part:
                extracted_info['pr_link'] = link_part
        
        elif line.startswith('* Repo link:') or line.startswith('Repo link:'):
            link_part = line.split(':', 1)[1].strip()
            if 'github.com' in link_part:
                extracted_info['repo_link'] = link_part
    
    return extracted_info

def _update_state_with_extracted_info(state: dict, extracted_info: dict) -> None:
    """
    Cập nhật state với thông tin extracted.
    
    Args:
        state: Session state dictionary
        extracted_info: Extracted information dictionary
    """
    # Cập nhật collected_info
    collected_info = state.get("collected_info", {})
    
    # Cập nhật task type
    if 'task_type' in extracted_info:
        if extracted_info['task_type'] == 'review_pr':
            state["user_task"] = "Review PR"
            collected_info['task'] = "Review PR"
        elif extracted_info['task_type'] == 'review_code':
            state["user_task"] = "Review source code"
            collected_info['task'] = "Review source code"
    
    # Cập nhật links
    if 'pr_link' in extracted_info:
        state["pr_link"] = extracted_info['pr_link']
        collected_info['pr_link'] = extracted_info['pr_link']
    
    if 'repo_link' in extracted_info:
        state["repo_link"] = extracted_info['repo_link']
        collected_info['repo_link'] = extracted_info['repo_link']
    
    # Xử lý user confirmation
    if 'user_confirmed' in extracted_info:
        state_dict = get_state_dict_safely(state)
        if StateManager.is_information_complete(state_dict):
            StateManager.set_information_confirmed(state_dict)
            StateManager.update_task_progress(state_dict, "confirmed", {"message": "User confirmed collected information"})
            # Update actual state
            state["information_collection_status"] = "confirmed"
    
    # Lưu lại collected_info
    state["collected_info"] = collected_info
    
    logger.info(f"Updated state with extracted info: {extracted_info}")

def _check_information_completeness(state: dict) -> None:
    """
    Kiểm tra xem đã collect đủ thông tin chưa và cập nhật status.
    
    Args:
        state: Session state dictionary
    """
    user_task = state.get("user_task", "")
    pr_link = state.get("pr_link", "")
    repo_link = state.get("repo_link", "")
    
    # Kiểm tra completeness dựa trên task type
    if user_task == "Review PR":
        if pr_link:
            state["information_collection_status"] = "collected"
            logger.info("Information collection completed for PR review task")
        else:
            state["information_collection_status"] = "collecting"
    
    elif user_task == "Review source code":
        if repo_link:
            state["information_collection_status"] = "collected"
            logger.info("Information collection completed for source code review task")
        else:
            state["information_collection_status"] = "collecting"
    
    else:
        state["information_collection_status"] = "collecting"

def _generate_confirmation_message_if_needed(state: dict, response_text: str) -> None:
    """
    Kiểm tra và tạo confirmation message nếu thông tin đã được collect đầy đủ.
    
    Args:
        state: Session state dictionary
        response_text: Agent response text
    """
    state_dict = get_state_dict_safely(state)
    if StateManager.is_information_complete(state_dict) and not StateManager.is_information_confirmed(state_dict):
        # Lưu confirmation message để có thể sử dụng sau
        user_task = state.get("user_task", "")
        pr_link = state.get("pr_link", "")
        repo_link = state.get("repo_link", "")
        
        confirmation_msg = f"""
Thông tin đã thu thập:
* Task: {user_task}
"""
        
        if user_task == "Review PR":
            confirmation_msg += f"* PR link: {pr_link}\n"
        elif user_task == "Review source code":
            confirmation_msg += f"* Repo link: {repo_link}\n"
        
        confirmation_msg += "\nVui lòng xác nhận thông tin trên là chính xác để tiếp tục."
        
        # Lưu confirmation message vào state
        state["pending_confirmation_message"] = confirmation_msg.strip()
        
        logger.info("Generated confirmation message for user")

def get_collected_information_summary(state: dict) -> str:
    """
    Tạo summary của thông tin đã collect được.
    
    Args:
        state: Session state dictionary
        
    Returns:
        String summary of collected information
    """
    user_task = state.get("user_task", "Not specified")
    pr_link = state.get("pr_link", "Not provided")
    repo_link = state.get("repo_link", "Not provided")
    
    summary = f"""
Thông tin đã thu thập:
* Task: {user_task}
"""
    
    if user_task == "Review PR":
        summary += f"* PR link: {pr_link}\n"
    elif user_task == "Review source code":
        summary += f"* Repo link: {repo_link}\n"
    
    return summary.strip()

# Export StateManager để các sub-agents có thể sử dụng
__all__ = ['root_agent', 'StateManager', 'get_collected_information_summary']

root_agent = Agent(
    model=GEMINI_MODEL,
    name='root_agent',
    description='Bạn là một Agent có chức năng điềù phối hoạt động của hệ thống Code Review',
    instruction="""
    Bạn là một Agent có chức năng điềù phối hoạt động của hệ thống Code Review
    Bạn có thể sử dụng các Agent khác và các tools để hoàn thành các nhiệm vụ của mình.
    
    Nhiệm vụ của bạn:
    - Collect toàn những thông tin cần thiết từ phía người dùng để hệ thống có thể hoạt động, các thông tin cần thiết bao gồm:
        + Nhiệm vụ mà người dùng muốn làm:
        {user_task}
        Hệ thống sẽ chỉ hỗ trợ 2 tasks là: Review PR (Pull request) và review toàn bộ source code.
        Nếu người dùng yêu cầu khác 2 nhiệm vụ này thì bạn cần phải từ chối và giải thích cho người dùng.
        
        + Nếu task là Review PR thì bạn cần phải collect thông tin sau:
            - Link PR: {pr_link}
        
        + Nếu task là review toàn bộ source code thì bạn cần phải collect thông tin sau:
            - Link repo: {repo_link}
        
    - Sau khi đã collect đủ thông tin, bạn cần phải hiển thị toàn bộ thông tin đó cho người dùng để confirm.
    Thông tin in ra cho người dùng sẽ định dạng:
    * Task: 
    * PR link or Repo link: 
    
    - Nếu người dùng confirm thông tin là đúng, bạn có thể proceed với các bước tiếp theo.
    - Nếu người dùng không confirm hoặc thông tin sai, bạn cần collect lại thông tin.
    
    - Khi thông tin đã được confirmed, bạn có thể delegate task cho các sub-agents phù hợp.
            
    """,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    )
