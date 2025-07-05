# Code Review Agent - Orchestrator với State Management

## Tổng quan

Hệ thống Code Review Agent này sử dụng ADK (Agent Development Kit) với một orchestrator agent có khả năng thu thập thông tin từ người dùng và chia sẻ state với các sub-agents. Hệ thống được thiết kế để xử lý hai loại task chính:

1. **Review Pull Request (PR)** - Phân tích và review các thay đổi trong PR
2. **Review Source Code** - Phân tích toàn bộ codebase của repository

## Kiến trúc

### 1. Orchestrator Agent (`agent.py`)
- **Mục đích**: Thu thập thông tin từ người dùng và điều phối các sub-agents
- **Callback System**: Sử dụng `before_agent_callback` và `after_agent_callback` để quản lý state
- **State Management**: Lưu trữ thông tin thu thập được và chia sẻ với sub-agents

### 2. State Manager (`state_manager.py`)
- **Mục đích**: Cung cấp utility functions để quản lý state
- **Chức năng chính**:
  - Đọc/ghi state
  - Validation thông tin
  - Tracking progress
  - Lưu trữ kết quả analysis

### 3. Sub-agent Examples (`subagent_example.py`)
- **Mục đích**: Minh họa cách sub-agents sử dụng state được share
- **Bao gồm**: PR Review Agent, Code Review Agent, và tools

## Cách hoạt động

### Luồng xử lý chính:

1. **Information Collection Phase**:
   - Orchestrator agent thu thập thông tin từ user
   - Sử dụng regex patterns để extract task type và links
   - Lưu thông tin vào state

2. **Validation Phase**:
   - Kiểm tra tính đầy đủ của thông tin
   - Tạo confirmation message cho user
   - Chờ user confirm

3. **Execution Phase**:
   - Sau khi user confirm, delegate task cho sub-agents
   - Sub-agents access state để lấy thông tin cần thiết
   - Lưu kết quả vào state

### State Structure:

```python
{
    "user_task": "Review PR" | "Review source code",
    "pr_link": "https://github.com/user/repo/pull/123",
    "repo_link": "https://github.com/user/repo",
    "information_collection_status": "collecting" | "collected" | "confirmed",
    "collected_info": {
        "task": "Review PR",
        "pr_link": "https://github.com/user/repo/pull/123"
    },
    "task_progress": {
        "current_stage": "pr_review_started",
        "timestamp": "2024-01-01T12:00:00",
        "details": {}
    },
    "analysis_results": {
        "pr_review": {
            "data": {},
            "timestamp": "2024-01-01T12:00:00"
        }
    }
}
```

## Callbacks System

### Before Agent Callback
```python
def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    - Khởi tạo state keys
    - Log state changes
    - Validate prerequisites
    """
```

### After Agent Callback
```python
def after_agent_callback(callback_context: CallbackContext, agent_response: types.Content) -> Optional[types.Content]:
    """
    - Extract thông tin từ response
    - Cập nhật state
    - Kiểm tra completeness
    - Tạo confirmation message
    """
```

## Cách sử dụng StateManager

### 1. Trong Callbacks:
```python
from .state_manager import StateManager, get_state_from_callback_context

def my_callback(callback_context: CallbackContext):
    state = get_state_from_callback_context(callback_context)
    
    # Kiểm tra thông tin đã complete chưa
    if StateManager.is_information_complete(state):
        # Proceed với next step
        pass
```

### 2. Trong Tools:
```python
from .state_manager import StateManager, get_state_from_tool_context

def my_tool(tool_context: ToolContext, param1: str):
    state = get_state_from_tool_context(tool_context)
    
    # Lấy thông tin cần thiết
    user_task = StateManager.get_user_task(state)
    pr_link = StateManager.get_pr_link(state)
    
    # Validation
    if not StateManager.is_information_confirmed(state):
        return {"error": "Information not confirmed"}
```

### 3. Tracking Progress:
```python
# Cập nhật progress
StateManager.update_task_progress(state, "analysis_started", {
    "repo_url": repo_url,
    "analysis_type": "security"
})

# Lưu kết quả analysis
StateManager.store_analysis_result(state, "security_scan", {
    "vulnerabilities": 5,
    "critical_issues": 2
})
```

## Sub-agents Integration

### Validation Prerequisites:
```python
def validate_subagent_prerequisites(state: Dict[str, Any], required_task: str) -> tuple[bool, str]:
    """
    Kiểm tra xem sub-agent có thể chạy không:
    - Thông tin đã được confirm
    - Task type matching
    - Required links available
    """
```

### Context Preparation:
```python
def prepare_context_for_subagent(state: Dict[str, Any]) -> str:
    """
    Tạo context string cho sub-agents:
    - Task information
    - Collection status
    - Required links
    """
```

## Example Usage

### 1. Khởi tạo Orchestrator Agent:
```python
from .agent import root_agent
from .state_manager import StateManager

# Agent đã được config với callbacks
# Sử dụng trong Runner
```

### 2. Tạo Sub-agent với State Access:
```python
from .subagent_example import pr_review_agent, validate_subagent_prerequisites

def my_subagent_callback(callback_context: CallbackContext):
    state = get_state_from_callback_context(callback_context)
    
    # Validate prerequisites
    is_valid, error_msg = validate_subagent_prerequisites(state, "Review PR")
    if not is_valid:
        return types.Content(parts=[types.Part(text=error_msg)])
    
    # Proceed with sub-agent logic
    pr_link = StateManager.get_pr_link(state)
    # ... xử lý PR review
```

### 3. Sử dụng trong Tools:
```python
from .subagent_example import code_review_tool_function

# Tool sẽ automatically access state và validate
result = code_review_tool_function(tool_context, repo_url, "security")
```

## Benefits

1. **Centralized State Management**: Tất cả state được quản lý tập trung
2. **Automatic Information Collection**: Tự động extract thông tin từ user input
3. **Validation & Confirmation**: Đảm bảo thông tin đầy đủ trước khi proceed
4. **Progress Tracking**: Theo dõi tiến trình xử lý
5. **Result Storage**: Lưu trữ kết quả từ các sub-agents
6. **Logging & Debugging**: Comprehensive logging cho debugging

## Mở rộng

Để thêm sub-agents mới:

1. Tạo callback functions sử dụng StateManager
2. Implement validation logic
3. Sử dụng utility functions từ state_manager
4. Lưu kết quả vào state cho các agents khác sử dụng

Hệ thống này cung cấp một foundation mạnh mẽ cho việc xây dựng complex multi-agent systems với state management và information sharing hiệu quả. 