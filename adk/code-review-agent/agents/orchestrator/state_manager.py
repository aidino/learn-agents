"""
State Manager for Code Review Agent System
Cung cấp các utility functions để quản lý và share state giữa các agents.
"""

import logging
from typing import Dict, Optional, Any
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

class StateManager:
    """
    Quản lý state cho Code Review Agent System.
    Cung cấp các methods để read/write state và share data giữa agents.
    """
    
    @staticmethod
    def get_user_task(state: Dict[str, Any]) -> str:
        """
        Lấy task mà user muốn thực hiện.
        
        Args:
            state: Session state dictionary
            
        Returns:
            User task string
        """
        return state.get("user_task", "")
    
    @staticmethod
    def get_pr_link(state: Dict[str, Any]) -> str:
        """
        Lấy PR link nếu task là review PR.
        
        Args:
            state: Session state dictionary
            
        Returns:
            PR link string
        """
        return state.get("pr_link", "")
    
    @staticmethod
    def get_repo_link(state: Dict[str, Any]) -> str:
        """
        Lấy repository link nếu task là review source code.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Repository link string
        """
        return state.get("repo_link", "")
    
    @staticmethod
    def get_collection_status(state: Dict[str, Any]) -> str:
        """
        Lấy trạng thái collection thông tin.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Collection status: 'collecting', 'collected', 'confirmed'
        """
        return state.get("information_collection_status", "collecting")
    
    @staticmethod
    def get_collected_info(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lấy toàn bộ thông tin đã collect được.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Dictionary containing collected information
        """
        return state.get("collected_info", {})
    
    @staticmethod
    def is_information_complete(state: Dict[str, Any]) -> bool:
        """
        Kiểm tra xem thông tin đã được collect đầy đủ chưa.
        
        Args:
            state: Session state dictionary
            
        Returns:
            True if information is complete, False otherwise
        """
        status = StateManager.get_collection_status(state)
        return status in ["collected", "confirmed"]
    
    @staticmethod
    def is_information_confirmed(state: Dict[str, Any]) -> bool:
        """
        Kiểm tra xem thông tin đã được user confirm chưa.
        
        Args:
            state: Session state dictionary
            
        Returns:
            True if information is confirmed, False otherwise
        """
        status = StateManager.get_collection_status(state)
        return status == "confirmed"
    
    @staticmethod
    def set_information_confirmed(state: Dict[str, Any]) -> None:
        """
        Đánh dấu thông tin đã được user confirm.
        
        Args:
            state: Session state dictionary
        """
        state["information_collection_status"] = "confirmed"
        logger.info("Information collection status set to confirmed")
    
    @staticmethod
    def get_task_context_for_subagent(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo context dictionary chứa thông tin cần thiết cho sub-agents.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Context dictionary for sub-agents
        """
        context = {
            "user_task": StateManager.get_user_task(state),
            "pr_link": StateManager.get_pr_link(state),
            "repo_link": StateManager.get_repo_link(state),
            "collection_status": StateManager.get_collection_status(state),
            "collected_info": StateManager.get_collected_info(state),
            "is_complete": StateManager.is_information_complete(state),
            "is_confirmed": StateManager.is_information_confirmed(state)
        }
        return context
    
    @staticmethod
    def update_task_progress(state: Dict[str, Any], stage: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Cập nhật progress của task execution.
        
        Args:
            state: Session state dictionary
            stage: Current stage of task execution
            details: Additional details about the progress
        """
        progress_key = "task_progress"
        if progress_key not in state:
            state[progress_key] = {}
        
        state[progress_key]["current_stage"] = stage
        state[progress_key]["timestamp"] = __import__('datetime').datetime.now().isoformat()
        
        if details:
            state[progress_key]["details"] = details
            
        logger.info(f"Task progress updated: {stage}")
    
    @staticmethod
    def get_task_progress(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lấy thông tin progress của task.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Task progress dictionary
        """
        return state.get("task_progress", {})
    
    @staticmethod
    def store_analysis_result(state: Dict[str, Any], result_type: str, result_data: Dict[str, Any]) -> None:
        """
        Lưu kết quả phân tích từ các sub-agents.
        
        Args:
            state: Session state dictionary
            result_type: Type of analysis result (e.g., 'pr_analysis', 'code_review')
            result_data: Analysis result data
        """
        results_key = "analysis_results"
        if results_key not in state:
            state[results_key] = {}
        
        state[results_key][result_type] = {
            "data": result_data,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
        logger.info(f"Analysis result stored: {result_type}")
    
    @staticmethod
    def get_analysis_result(state: Dict[str, Any], result_type: str) -> Optional[Dict[str, Any]]:
        """
        Lấy kết quả phân tích đã lưu.
        
        Args:
            state: Session state dictionary
            result_type: Type of analysis result to retrieve
            
        Returns:
            Analysis result data or None if not found
        """
        results = state.get("analysis_results", {})
        return results.get(result_type, {}).get("data")
    
    @staticmethod
    def get_all_analysis_results(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lấy tất cả kết quả phân tích.
        
        Args:
            state: Session state dictionary
            
        Returns:
            Dictionary containing all analysis results
        """
        return state.get("analysis_results", {})


# Utility functions for use in callbacks and tools
def get_state_from_callback_context(callback_context: CallbackContext) -> Dict[str, Any]:
    """
    Extract state dictionary from CallbackContext.
    
    Args:
        callback_context: ADK CallbackContext object
        
    Returns:
        State dictionary
    """
    return dict(callback_context.state)

def get_state_from_tool_context(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extract state dictionary from ToolContext.
    
    Args:
        tool_context: ADK ToolContext object
        
    Returns:
        State dictionary
    """
    return dict(tool_context.state)

def prepare_context_for_subagent(state: Dict[str, Any]) -> str:
    """
    Tạo context string có thể được pass cho sub-agents.
    
    Args:
        state: Session state dictionary
        
    Returns:
        Context string for sub-agents
    """
    context = StateManager.get_task_context_for_subagent(state)
    
    context_str = f"""
Context từ Orchestrator Agent:
- Task: {context['user_task']}
- Collection Status: {context['collection_status']}
- Information Complete: {context['is_complete']}
- Information Confirmed: {context['is_confirmed']}
"""
    
    if context['user_task'] == "Review PR" and context['pr_link']:
        context_str += f"- PR Link: {context['pr_link']}\n"
    elif context['user_task'] == "Review source code" and context['repo_link']:
        context_str += f"- Repository Link: {context['repo_link']}\n"
    
    return context_str.strip()

def log_state_change(state: Dict[str, Any], action: str, details: Optional[str] = None) -> None:
    """
    Log state changes for debugging purposes.
    
    Args:
        state: Session state dictionary
        action: Description of the action that caused the state change
        details: Additional details about the change
    """
    log_msg = f"State change - Action: {action}"
    if details:
        log_msg += f", Details: {details}"
    
    # Log current state summary
    task = state.get("user_task", "Not set")
    status = state.get("information_collection_status", "Not set")
    log_msg += f", Current Task: {task}, Status: {status}"
    
    logger.info(log_msg) 