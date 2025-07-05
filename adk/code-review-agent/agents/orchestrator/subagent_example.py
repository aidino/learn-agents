"""
Example Sub-Agent cho Code Review System
Minh họa cách sub-agents có thể sử dụng state được share từ orchestrator agent.
"""

import logging
from typing import Optional, Dict, Any
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# Import StateManager từ orchestrator
from .state_manager import StateManager, get_state_from_callback_context, get_state_from_tool_context, prepare_context_for_subagent, log_state_change

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.0-flash-001'

def pr_review_before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback cho PR Review Agent để access state từ orchestrator.
    
    Args:
        callback_context: ADK CallbackContext
        
    Returns:
        Optional content để modify agent behavior
    """
    try:
        # Lấy state từ callback context
        state = get_state_from_callback_context(callback_context)
        
        # Kiểm tra xem thông tin đã được confirm chưa
        if not StateManager.is_information_confirmed(state):
            logger.warning("PR Review Agent called but information not confirmed yet")
            return types.Content(parts=[
                types.Part(text="Thông tin chưa được xác nhận. Vui lòng confirm thông tin trước khi tiếp tục.")
            ])
        
        # Lấy thông tin cần thiết cho PR review
        user_task = StateManager.get_user_task(state)
        pr_link = StateManager.get_pr_link(state)
        
        if user_task != "Review PR":
            logger.warning(f"PR Review Agent called but task is: {user_task}")
            return types.Content(parts=[
                types.Part(text=f"Agent này chỉ xử lý task 'Review PR', nhưng task hiện tại là: {user_task}")
            ])
        
        if not pr_link:
            logger.warning("PR Review Agent called but no PR link available")
            return types.Content(parts=[
                types.Part(text="Không có PR link để review. Vui lòng cung cấp PR link.")
            ])
        
        # Cập nhật progress
        StateManager.update_task_progress(callback_context.state, "pr_review_started", {
            "pr_link": pr_link,
            "agent": "PR Review Agent"
        })
        
        log_state_change(dict(callback_context.state), "pr_review_started", f"PR Review Agent started for: {pr_link}")
        
        logger.info(f"PR Review Agent starting review for: {pr_link}")
        
    except Exception as e:
        logger.error(f"Error in PR Review Agent before callback: {e}")
        return types.Content(parts=[
            types.Part(text=f"Lỗi khi khởi tạo PR Review Agent: {str(e)}")
        ])
    
    return None

def pr_review_after_agent_callback(callback_context: CallbackContext, agent_response: types.Content) -> Optional[types.Content]:
    """
    Callback sau khi PR Review Agent hoàn thành.
    
    Args:
        callback_context: ADK CallbackContext
        agent_response: Response từ agent
        
    Returns:
        Optional modified content
    """
    try:
        # Lấy state và lưu kết quả
        state = callback_context.state
        
        # Extract response text
        response_text = ""
        if agent_response and agent_response.parts:
            for part in agent_response.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
        
        # Lưu kết quả PR review vào state
        pr_link = StateManager.get_pr_link(state)
        review_result = {
            "pr_link": pr_link,
            "review_content": response_text,
            "status": "completed"
        }
        
        StateManager.store_analysis_result(state, "pr_review", review_result)
        StateManager.update_task_progress(state, "pr_review_completed", {
            "pr_link": pr_link,
            "result_length": len(response_text)
        })
        
        log_state_change(dict(state), "pr_review_completed", f"PR Review completed for: {pr_link}")
        
        logger.info(f"PR Review Agent completed review for: {pr_link}")
        
    except Exception as e:
        logger.error(f"Error in PR Review Agent after callback: {e}")
    
    return None

def code_review_tool_function(tool_context: ToolContext, repository_url: str, analysis_type: str = "full") -> Dict[str, Any]:
    """
    Example tool function cho code review.
    Minh họa cách tools có thể access state.
    
    Args:
        tool_context: ADK ToolContext
        repository_url: URL của repository cần review
        analysis_type: Loại phân tích (full, security, performance)
        
    Returns:
        Dictionary chứa kết quả analysis
    """
    try:
        # Lấy state từ tool context
        state = get_state_from_tool_context(tool_context)
        
        # Kiểm tra xem thông tin đã được confirm chưa
        if not StateManager.is_information_confirmed(state):
            return {
                "error": "Information not confirmed",
                "message": "Thông tin chưa được xác nhận. Vui lòng confirm trước khi tiếp tục."
            }
        
        # Lấy thông tin từ state
        user_task = StateManager.get_user_task(state)
        repo_link = StateManager.get_repo_link(state)
        
        # Validate task type
        if user_task != "Review source code":
            return {
                "error": "Invalid task type",
                "message": f"Tool này chỉ xử lý task 'Review source code', nhưng task hiện tại là: {user_task}"
            }
        
        # Validate repository URL
        if repository_url != repo_link:
            logger.warning(f"Repository URL mismatch: tool={repository_url}, state={repo_link}")
        
        # Cập nhật progress
        StateManager.update_task_progress(tool_context.state, "code_analysis_started", {
            "repo_url": repository_url,
            "analysis_type": analysis_type
        })
        
        # Simulate code analysis (trong thực tế sẽ gọi actual analysis tools)
        logger.info(f"Starting {analysis_type} code analysis for: {repository_url}")
        
        # Mock analysis result
        analysis_result = {
            "repository_url": repository_url,
            "analysis_type": analysis_type,
            "status": "completed",
            "findings": [
                {
                    "type": "security",
                    "severity": "medium",
                    "description": "Potential SQL injection vulnerability found",
                    "file": "src/database/queries.py",
                    "line": 45
                },
                {
                    "type": "performance",
                    "severity": "low",
                    "description": "Inefficient loop detected",
                    "file": "src/utils/helpers.py",
                    "line": 123
                }
            ],
            "summary": {
                "total_files_analyzed": 156,
                "total_issues_found": 2,
                "security_issues": 1,
                "performance_issues": 1
            }
        }
        
        # Lưu kết quả vào state
        StateManager.store_analysis_result(tool_context.state, "code_analysis", analysis_result)
        StateManager.update_task_progress(tool_context.state, "code_analysis_completed", {
            "repo_url": repository_url,
            "total_issues": analysis_result["summary"]["total_issues_found"]
        })
        
        log_state_change(dict(tool_context.state), "code_analysis_completed", f"Analysis completed for: {repository_url}")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in code review tool: {e}")
        return {
            "error": "Analysis failed",
            "message": f"Lỗi khi phân tích code: {str(e)}"
        }

# Tạo PR Review Agent
pr_review_agent = Agent(
    model=GEMINI_MODEL,
    name='pr_review_agent',
    description='Agent chuyên xử lý review Pull Request',
    instruction="""
    Bạn là một Agent chuyên xử lý review Pull Request.
    
    Nhiệm vụ của bạn:
    - Phân tích Pull Request được cung cấp
    - Đưa ra nhận xét về code changes
    - Kiểm tra code quality, security issues, và best practices
    - Đưa ra suggestions để improve code
    
    Bạn sẽ nhận được PR link từ orchestrator agent thông qua state.
    """,
    before_agent_callback=pr_review_before_agent_callback,
    after_agent_callback=pr_review_after_agent_callback,
)

# Tạo Code Review Agent
code_review_agent = Agent(
    model=GEMINI_MODEL,
    name='code_review_agent',
    description='Agent chuyên xử lý review toàn bộ source code',
    instruction="""
    Bạn là một Agent chuyên xử lý review toàn bộ source code repository.
    
    Nhiệm vụ của bạn:
    - Phân tích toàn bộ codebase
    - Kiểm tra architecture và design patterns
    - Tìm security vulnerabilities
    - Đánh giá performance và scalability
    - Đưa ra recommendations cho improvement
    
    Bạn có thể sử dụng các tools để phân tích code và sẽ nhận thông tin repository từ orchestrator agent.
    """,
    tools=[code_review_tool_function],
)

def get_context_summary_for_subagent(state: Dict[str, Any]) -> str:
    """
    Tạo context summary cho sub-agents.
    
    Args:
        state: Session state dictionary
        
    Returns:
        Context summary string
    """
    return prepare_context_for_subagent(state)

def validate_subagent_prerequisites(state: Dict[str, Any], required_task: str) -> tuple[bool, str]:
    """
    Validate xem sub-agent có thể chạy không.
    
    Args:
        state: Session state dictionary
        required_task: Task type required by sub-agent
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Kiểm tra thông tin đã được confirm
    if not StateManager.is_information_confirmed(state):
        return False, "Thông tin chưa được user confirm"
    
    # Kiểm tra task type
    current_task = StateManager.get_user_task(state)
    if current_task != required_task:
        return False, f"Task type mismatch. Required: {required_task}, Current: {current_task}"
    
    # Kiểm tra thông tin cần thiết
    if required_task == "Review PR":
        pr_link = StateManager.get_pr_link(state)
        if not pr_link:
            return False, "PR link không có"
    elif required_task == "Review source code":
        repo_link = StateManager.get_repo_link(state)
        if not repo_link:
            return False, "Repository link không có"
    
    return True, ""

# Export cho sử dụng
__all__ = [
    'pr_review_agent', 
    'code_review_agent', 
    'code_review_tool_function',
    'get_context_summary_for_subagent',
    'validate_subagent_prerequisites'
] 