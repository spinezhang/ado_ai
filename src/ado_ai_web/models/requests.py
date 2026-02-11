"""API request models for ADO AI Web Service."""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class SetupRequest(BaseModel):
    """Request model for initial setup."""

    username: str = Field(default="default", min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)

    # Azure DevOps configuration
    azure_devops_org_url: HttpUrl = Field(..., description="Azure DevOps organization URL")
    azure_devops_project: str = Field(..., min_length=1, max_length=255, description="Project name")
    azure_devops_pat: str = Field(..., min_length=1, description="Personal Access Token")

    # Anthropic API configuration (optional - falls back to system config)
    anthropic_api_key: Optional[str] = Field(default=None, min_length=1, description="Anthropic API key (optional if configured in system config)")

    # Optional settings
    work_folder_path: Optional[str] = Field(default=None, max_length=1000)
    claude_model: str = Field(default="claude-opus-4-6", max_length=100)
    auto_approve: bool = Field(default=False)
    max_tokens: int = Field(default=4096, ge=100, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "default",
                "azure_devops_org_url": "https://dev.azure.com/myorg",
                "azure_devops_project": "MyProject",
                "azure_devops_pat": "your-pat-token-here",
                "anthropic_api_key": "your-api-key-here",
                "work_folder_path": "/path/to/workspace",
                "claude_model": "claude-opus-4-6"
            }
        }
    }


class UpdateConfigRequest(BaseModel):
    """Request model for updating configuration (partial updates)."""

    azure_devops_org_url: Optional[HttpUrl] = None
    azure_devops_project: Optional[str] = Field(default=None, min_length=1, max_length=255)
    azure_devops_pat: Optional[str] = Field(default=None, min_length=1)
    anthropic_api_key: Optional[str] = Field(default=None, min_length=1)
    work_folder_path: Optional[str] = Field(default=None, max_length=1000)
    claude_model: Optional[str] = Field(default=None, max_length=100)
    auto_approve: Optional[bool] = None
    max_tokens: Optional[int] = Field(default=None, ge=100, le=8192)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class TestConnectionRequest(BaseModel):
    """Request model for testing connectivity."""

    service: str = Field(..., description="Service to test: 'azure_devops' or 'anthropic'")

    # For testing without saving (optional overrides)
    azure_devops_org_url: Optional[HttpUrl] = None
    azure_devops_project: Optional[str] = None
    azure_devops_pat: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class AnalyzeWorkItemRequest(BaseModel):
    """Request model for analyzing a work item."""

    work_item_id: int = Field(..., gt=0, description="Work item ID")
    custom_prompt: Optional[str] = Field(default=None, max_length=5000, description="Additional instructions for AI")
    work_folder_path: Optional[str] = Field(default=None, max_length=1000, description="Work folder for file operations")
    include_files: Optional[list[str]] = Field(default=None, description="File paths to include in context")


class CompleteWorkItemRequest(BaseModel):
    """Request model for completing a work item."""

    approve: bool = Field(..., description="User approval to apply changes")
    modified_analysis: Optional[dict] = Field(default=None, description="User-edited analysis fields")


class WriteFileRequest(BaseModel):
    """Request model for writing file content."""

    content: str = Field(..., description="File content to write")
    encoding: str = Field(default="utf-8", max_length=50)
