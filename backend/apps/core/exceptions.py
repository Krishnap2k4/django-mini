class TaskWorkflowError(Exception):
    """Base exception for workflow errors."""
    pass

class InvalidTransitionError(TaskWorkflowError):
    """Raised when a task status transition is not allowed."""
    pass

class PermissionDeniedError(TaskWorkflowError):
    """Raised when an actor does not have permission for an action."""
    pass