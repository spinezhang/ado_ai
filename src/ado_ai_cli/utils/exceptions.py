"""Custom exceptions for the ADO AI CLI application."""


class AdoAiError(Exception):
    """Base exception for all application errors."""

    pass


class ConfigurationError(AdoAiError):
    """Configuration validation errors."""

    pass


class AzureDevOpsError(AdoAiError):
    """Azure DevOps API errors."""

    pass


class WorkItemNotFoundError(AzureDevOpsError):
    """Work item does not exist."""

    def __init__(self, work_item_id: int):
        self.work_item_id = work_item_id
        super().__init__(f"Work item {work_item_id} not found")


class AuthenticationError(AdoAiError):
    """Authentication failures."""

    pass


class ClaudeAPIError(AdoAiError):
    """Claude API errors."""

    pass


class RateLimitError(AdoAiError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        message = "API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


class WorkflowError(AdoAiError):
    """Workflow execution errors."""

    pass
