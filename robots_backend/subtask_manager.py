"""
Subtask management system for the coding agent.
This system allows the agent to break down complex tasks into smaller subtasks
and track progress through them systematically.
"""

import json
import os
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class SubTask:
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SubTaskManager:
    """
    Manages subtasks for complex coding operations.
    Break down tasks into smaller, manageable pieces.
    """
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.tasks: Dict[str, SubTask] = {}
        self.task_order: List[str] = []
        self.current_task_id: Optional[str] = None
        self.storage_file = f"subtasks_{conversation_id}.json"
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from persistent storage."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                for task_data in data.get('tasks', []):
                    task = SubTask(
                        id=task_data['id'],
                        title=task_data['title'],
                        description=task_data['description'],
                        status=TaskStatus(task_data['status']),
                        created_at=task_data.get('created_at', time.time()),
                        started_at=task_data.get('started_at'),
                        completed_at=task_data.get('completed_at'),
                        result=task_data.get('result'),
                        error=task_data.get('error'),
                        dependencies=task_data.get('dependencies', []),
                        metadata=task_data.get('metadata', {})
                    )
                    self.tasks[task.id] = task
                
                self.task_order = data.get('task_order', [])
                self.current_task_id = data.get('current_task_id')
                
        except Exception as e:
            print(f"Could not load subtasks: {e}")
    
    def _save_tasks(self):
        """Save tasks to persistent storage."""
        try:
            data = {
                'tasks': [],
                'task_order': self.task_order,
                'current_task_id': self.current_task_id,
                'last_updated': time.time()
            }
            
            for task in self.tasks.values():
                task_data = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status.value,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                    'result': task.result,
                    'error': task.error,
                    'dependencies': task.dependencies,
                    'metadata': task.metadata
                }
                data['tasks'].append(task_data)
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Could not save subtasks: {e}")
    
    def create_task_plan(self, main_task: str, subtasks: List[Dict[str, Any]]) -> str:
        """
        Create a plan with multiple subtasks.
        
        Args:
            main_task: Description of the main task
            subtasks: List of subtask dictionaries with 'title', 'description', and optional 'dependencies'
        
        Returns:
            Formatted task plan string
        """
        # Clear existing tasks for new plan
        self.tasks.clear()
        self.task_order.clear()
        self.current_task_id = None
        
        # Create subtasks
        for i, subtask_data in enumerate(subtasks):
            task_id = f"task_{i+1:02d}"
            
            task = SubTask(
                id=task_id,
                title=subtask_data['title'],
                description=subtask_data['description'],
                dependencies=subtask_data.get('dependencies', []),
                metadata=subtask_data.get('metadata', {})
            )
            
            self.tasks[task_id] = task
            self.task_order.append(task_id)
        
        self._save_tasks()
        
        # Generate formatted plan
        plan_lines = [
            f"📋 **Task Plan: {main_task}**",
            "",
            "I've broken this down into the following subtasks:",
            ""
        ]
        
        for i, task_id in enumerate(self.task_order, 1):
            task = self.tasks[task_id]
            status_icon = self._get_status_icon(task.status)
            plan_lines.append(f"{i}. {status_icon} **{task.title}**")
            plan_lines.append(f"   {task.description}")
            if task.dependencies:
                deps = [self.tasks[dep_id].title for dep_id in task.dependencies if dep_id in self.tasks]
                plan_lines.append(f"   *Depends on: {', '.join(deps)}*")
            plan_lines.append("")
        
        plan_lines.extend([
            "I'll work through these tasks systematically, updating you on progress as I go.",
            "",
            "Let me start with the first task..."
        ])
        
        return "\n".join(plan_lines)
    
    def start_next_task(self) -> Optional[SubTask]:
        """Start the next available task."""
        # Find next pending task that has all dependencies completed
        for task_id in self.task_order:
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_completed = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED 
                for dep_id in task.dependencies 
                if dep_id in self.tasks
            )
            
            if deps_completed:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                self.current_task_id = task_id
                self._save_tasks()
                return task
        
        return None
    
    def complete_current_task(self, result: str = "") -> Optional[SubTask]:
        """Mark the current task as completed."""
        if not self.current_task_id or self.current_task_id not in self.tasks:
            return None
        
        task = self.tasks[self.current_task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        
        self.current_task_id = None
        self._save_tasks()
        
        return task
    
    def fail_current_task(self, error: str) -> Optional[SubTask]:
        """Mark the current task as failed."""
        if not self.current_task_id or self.current_task_id not in self.tasks:
            return None
        
        task = self.tasks[self.current_task_id]
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        task.error = error
        
        self.current_task_id = None
        self._save_tasks()
        
        return task
    
    def get_progress_summary(self) -> str:
        """Get a formatted progress summary."""
        if not self.tasks:
            return "No active task plan."
        
        completed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        in_progress = sum(1 for task in self.tasks.values() if task.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
        
        total = len(self.tasks)
        
        lines = [
            f"📊 **Progress Summary** ({completed}/{total} completed)",
            ""
        ]
        
        for i, task_id in enumerate(self.task_order, 1):
            task = self.tasks[task_id]
            status_icon = self._get_status_icon(task.status)
            
            line = f"{i}. {status_icon} {task.title}"
            if task.status == TaskStatus.IN_PROGRESS:
                line += " *(currently working on this)*"
            elif task.status == TaskStatus.COMPLETED and task.result:
                line += f" ✓"
            elif task.status == TaskStatus.FAILED and task.error:
                line += f" ❌ ({task.error})"
            
            lines.append(line)
        
        if in_progress > 0:
            lines.append("")
            lines.append("🔄 Currently working on the highlighted task above.")
        elif pending > 0:
            lines.append("")
            lines.append("⏳ Ready to continue with the next pending task.")
        elif completed == total:
            lines.append("")
            lines.append("🎉 All tasks completed successfully!")
        
        return "\n".join(lines)
    
    def get_current_task(self) -> Optional[SubTask]:
        """Get the currently active task."""
        if self.current_task_id and self.current_task_id in self.tasks:
            return self.tasks[self.current_task_id]
        return None
    
    def has_active_plan(self) -> bool:
        """Check if there's an active task plan."""
        return len(self.tasks) > 0
    
    def is_plan_complete(self) -> bool:
        """Check if all tasks in the plan are completed."""
        if not self.tasks:
            return False
        
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED] 
            for task in self.tasks.values()
        )
    
    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get emoji icon for task status."""
        icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.SKIPPED: "⏭️"
        }
        return icons.get(status, "❓")
    
    def cleanup(self):
        """Clean up task files."""
        try:
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
        except Exception as e:
            print(f"Could not cleanup subtask file: {e}")

# Global subtask managers (keyed by conversation_id)
_subtask_managers: Dict[str, SubTaskManager] = {}

def get_subtask_manager(conversation_id: str) -> SubTaskManager:
    """Get or create a subtask manager for a conversation."""
    if conversation_id not in _subtask_managers:
        _subtask_managers[conversation_id] = SubTaskManager(conversation_id)
    return _subtask_managers[conversation_id]