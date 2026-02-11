"""API response models for ADO AI Web Service."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class SetupResponse(BaseModel):
    """Response model for setup completion."""

    success: bool
    message: str
    user_id: int
    username: str


class ConfigResponse(BaseModel):
    """Response model for configuration retrieval."""

    azure_devops_org_url: str
    azure_devops_project: str
    azure_devops_pat: str = "***REDACTED***"
    anthropic_api_key: str = "***REDACTED***"
    claude_model: str
    work_folder_path: Optional[str] = None
    auto_approve: bool
    max_tokens: int
    temperature: float
    is_configured: bool


class TestConnectionResponse(BaseModel):
    """Response model for connection testing."""

    success: bool
    service: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int


class WorkItemResponse(BaseModel):
    """Response model for work item details."""

    work_item_id: int
    work_item_type: str
    title: str
    state: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[int] = None
    remaining_work: Optional[float] = None
    tags: Optional[str] = None
    url: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response model for AI analysis results."""

    work_item_id: int
    status: str  # 'analyzing', 'completed', 'failed'
    analysis: Optional[dict] = None  # Full AnalysisResult
    token_usage: Optional[dict] = None
    cost: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class FileTreeNode(BaseModel):
    """Response model for file tree node."""

    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: Optional[int] = None
    modified: Optional[datetime] = None
    children: Optional[list['FileTreeNode']] = None

    model_config = {
        "from_attributes": True
    }


class FileContentResponse(BaseModel):
    """Response model for file content."""

    path: str
    content: str
    encoding: str = "utf-8"
    language: Optional[str] = None  # For syntax highlighting
    size: int


class WorkItemHistoryResponse(BaseModel):
    """Response model for work item history list."""

    items: list[dict]
    total: int
    page: int = 1
    page_size: int = 20


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str
    service: str
    timestamp: Optional[datetime] = None
