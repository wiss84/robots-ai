"""
Subtask management tool for the coding agent.
This tool allows the agent to create, manage, and track subtasks
to break down complex tasks.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from subtask_manager import get_subtask_manager, TaskStatus

class CreateTaskPlanInput(BaseModel):
    main_task: str = Field(..., description="Description of the main task to be broken down")
    subtasks: List[Dict[str, Any]] = Field(..., description="List of subtasks with 'title', 'description', and optional 'dependencies'")
    conversation_id: str = Field(..., description="Conversation ID to associate with this task plan")

class TaskProgressInput(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    action: str = Field(..., description="Action to perform: 'start_next', 'complete_current', 'fail_current', 'get_progress'")
    result: Optional[str] = Field(None, description="Result description for completed tasks")
    error: Optional[str] = Field(None, description="Error description for failed tasks")

@tool("create_task_plan", args_schema=CreateTaskPlanInput)
def create_task_plan(main_task: str, subtasks: List[Dict[str, Any]], conversation_id: str) -> dict:
    """
    Create a structured task plan by breaking down a complex task into manageable subtasks.
    This helps organize work systematically and track progress.
    
    Example subtasks format:
    [
        {"title": "Analyze requirements", "description": "Review and understand the task requirements"},
        {"title": "Design solution", "description": "Create a technical design for the implementation"},
        {"title": "Implement core logic", "description": "Write the main functionality", "dependencies": ["task_02"]},
        {"title": "Update documentation", "description": "Document the new functionality"}
    ]
    """
    try:
        manager = get_subtask_manager(conversation_id)
        plan_text = manager.create_task_plan(main_task, subtasks)
        
        return {
            "success": True,
            "plan": plan_text,
            "total_tasks": len(subtasks),
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create task plan: {str(e)}"
        }

@tool("manage_task_progress", args_schema=TaskProgressInput)
def manage_task_progress(conversation_id: str, action: str, result: Optional[str] = None, error: Optional[str] = None) -> dict:
    """
    Manage task progress by starting next tasks, completing current tasks, or getting progress updates.
    
    Actions:
    - 'start_next': Start the next available task
    - 'complete_current': Mark the current task as completed
    - 'fail_current': Mark the current task as failed
    - 'get_progress': Get current progress summary
    """
    try:
        manager = get_subtask_manager(conversation_id)
        
        if not manager.has_active_plan():
            return {
                "success": False,
                "error": "No active task plan found. Create a task plan first."
            }
        
        if action == "start_next":
            task = manager.start_next_task()
            if task:
                return {
                    "success": True,
                    "action": "started_task",
                    "current_task": {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description
                    },
                    "message": f"🔄 **Started Task:** {task.title}\n\n{task.description}\n\nLet me work on this now..."
                }
            else:
                if manager.is_plan_complete():
                    return {
                        "success": True,
                        "action": "plan_complete",
                        "message": "🎉 **All tasks completed!** The task plan has been finished successfully."
                    }
                else:
                    return {
                        "success": False,
                        "error": "No available tasks to start. Check dependencies or task status."
                    }
        
        elif action == "complete_current":
            task = manager.complete_current_task(result or "Task completed successfully")
            if task:
                progress = manager.get_progress_summary()
                next_task = manager.start_next_task()
                
                response = {
                    "success": True,
                    "action": "completed_task",
                    "completed_task": {
                        "id": task.id,
                        "title": task.title,
                        "result": task.result
                    },
                    "progress": progress
                }
                
                if next_task:
                    response["next_task"] = {
                        "id": next_task.id,
                        "title": next_task.title,
                        "description": next_task.description
                    }
                    response["message"] = f"✅ **Completed:** {task.title}\n\n{progress}\n\n🔄 **Next Task:** {next_task.title}\n\n{next_task.description}"
                else:
                    if manager.is_plan_complete():
                        response["message"] = f"✅ **Completed:** {task.title}\n\n{progress}\n\n🎉 **All tasks completed!**"
                    else:
                        response["message"] = f"✅ **Completed:** {task.title}\n\n{progress}"
                
                return response
            else:
                return {
                    "success": False,
                    "error": "No current task to complete"
                }
        
        elif action == "fail_current":
            task = manager.fail_current_task(error or "Task failed")
            if task:
                progress = manager.get_progress_summary()
                return {
                    "success": True,
                    "action": "failed_task",
                    "failed_task": {
                        "id": task.id,
                        "title": task.title,
                        "error": task.error
                    },
                    "progress": progress,
                    "message": f"❌ **Failed:** {task.title}\n\nError: {task.error}\n\n{progress}"
                }
            else:
                return {
                    "success": False,
                    "error": "No current task to fail"
                }
        
        elif action == "get_progress":
            progress = manager.get_progress_summary()
            current_task = manager.get_current_task()
            
            response = {
                "success": True,
                "action": "progress_update",
                "progress": progress,
                "has_active_plan": manager.has_active_plan(),
                "is_complete": manager.is_plan_complete()
            }
            
            if current_task:
                response["current_task"] = {
                    "id": current_task.id,
                    "title": current_task.title,
                    "description": current_task.description,
                    "status": current_task.status.value
                }
            
            return response
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Valid actions: start_next, complete_current, fail_current, get_progress"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Task management failed: {str(e)}"
        }

@tool("get_task_suggestions")
def get_task_suggestions(task_description: str) -> dict:
    """
    Get suggestions for breaking down a complex task into subtasks.
    This helps with task planning by providing common patterns and best practices.
    """
    try:
        # Common task breakdown patterns
        suggestions = {
            "web_development": [
                {"title": "Analyze requirements", "description": "Review and understand the project requirements"},
                {"title": "Set up project structure", "description": "Create the basic project structure and configuration"},
                {"title": "Design components", "description": "Plan the component architecture and data flow"},
                {"title": "Implement core functionality", "description": "Build the main features and logic"},
                {"title": "Add styling", "description": "Implement the visual design and responsive layout"},
                {"title": "Optimize performance", "description": "Review and optimize for performance"},
                {"title": "Update documentation", "description": "Document the implementation and usage"}
            ],
            "api_development": [
                {"title": "Design API schema", "description": "Define endpoints, request/response formats"},
                {"title": "Set up database models", "description": "Create data models and database schema"},
                {"title": "Implement endpoints", "description": "Build the API endpoints and business logic"},
                {"title": "Add authentication", "description": "Implement user authentication and authorization"},
                {"title": "Add validation", "description": "Implement input validation and error handling"},
                {"title": "Add documentation", "description": "Create API documentation"}
            ],
            "bug_fix": [
                {"title": "Reproduce the issue", "description": "Understand and reproduce the reported bug"},
                {"title": "Analyze root cause", "description": "Investigate the code to find the root cause"},
                {"title": "Design solution", "description": "Plan the fix approach and consider side effects"},
                {"title": "Implement fix", "description": "Apply the fix to the codebase"},
            ],
            "refactoring": [
                {"title": "Analyze current code", "description": "Review the existing code structure and identify issues"},
                {"title": "Plan refactoring approach", "description": "Design the new structure and migration strategy"},
                {"title": "Refactor incrementally", "description": "Apply changes in small, manageable steps"},
                {"title": "Update documentation", "description": "Update docs to reflect the new structure"}
            ]
        }
        
        # Simple keyword matching to suggest appropriate pattern
        task_lower = task_description.lower()
        
        if any(keyword in task_lower for keyword in ['web', 'frontend', 'react', 'vue', 'angular']):
            pattern = "web_development"
        elif any(keyword in task_lower for keyword in ['api', 'backend', 'server', 'endpoint']):
            pattern = "api_development"
        elif any(keyword in task_lower for keyword in ['bug', 'fix', 'error', 'issue']):
            pattern = "bug_fix"
        elif any(keyword in task_lower for keyword in ['refactor', 'restructure', 'optimize', 'clean']):
            pattern = "refactoring"
        else:
            pattern = "web_development"  # Default
        
        return {
            "success": True,
            "task_description": task_description,
            "suggested_pattern": pattern,
            "subtasks": suggestions[pattern],
            "note": "These are suggested subtasks. Modify them based on your specific requirements."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get task suggestions: {str(e)}"
        }