"""Data models for Azure DevOps work items."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkItem(BaseModel):
    """Represents an Azure DevOps work item."""

    id: int = Field(..., description="Work item ID")
    work_item_type: str = Field(..., description="Type of work item (Bug, Task, User Story, etc.)")
    title: str = Field(..., description="Work item title")
    state: str = Field(..., description="Current state (Active, Resolved, Closed, etc.)")
    description: Optional[str] = Field(None, description="Work item description/repro steps")
    assigned_to: Optional[str] = Field(None, description="Person assigned to the work item")
    created_by: Optional[str] = Field(None, description="Person who created the work item")
    created_date: Optional[datetime] = Field(None, description="Date when work item was created")
    changed_date: Optional[datetime] = Field(None, description="Date when work item was last changed")
    area_path: Optional[str] = Field(None, description="Area path")
    iteration_path: Optional[str] = Field(None, description="Iteration path")
    tags: Optional[str] = Field(None, description="Work item tags")
    priority: Optional[int] = Field(None, description="Priority level")
    remaining_work: Optional[float] = Field(None, description="Remaining work in hours")
    completed_work: Optional[float] = Field(None, description="Completed work in hours")
    acceptance_criteria: Optional[str] = Field(None, description="Acceptance criteria")
    repro_steps: Optional[str] = Field(None, description="Reproduction steps (for bugs)")
    system_info: Optional[str] = Field(None, description="System information (for bugs)")
    url: Optional[str] = Field(None, description="URL to view work item in browser")
    raw_fields: Dict[str, Any] = Field(default_factory=dict, description="Raw fields from API")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True

    def get_context_for_ai(self) -> str:
        """
        Generate a formatted context string suitable for AI analysis.

        Returns:
            Formatted string with work item details
        """
        context_parts = [
            f"Work Item ID: {self.id}",
            f"Type: {self.work_item_type}",
            f"Title: {self.title}",
            f"State: {self.state}",
        ]

        if self.description:
            context_parts.append(f"Description:\n{self.description}")

        if self.acceptance_criteria:
            context_parts.append(f"Acceptance Criteria:\n{self.acceptance_criteria}")

        if self.repro_steps:
            context_parts.append(f"Reproduction Steps:\n{self.repro_steps}")

        if self.system_info:
            context_parts.append(f"System Info:\n{self.system_info}")

        if self.assigned_to:
            context_parts.append(f"Assigned To: {self.assigned_to}")

        if self.priority:
            context_parts.append(f"Priority: {self.priority}")

        if self.remaining_work is not None:
            context_parts.append(f"Remaining Work: {self.remaining_work} hours")

        if self.tags:
            context_parts.append(f"Tags: {self.tags}")

        return "\n\n".join(context_parts)


class WorkItemComment(BaseModel):
    """Represents a comment on a work item."""

    id: int = Field(..., description="Comment ID")
    text: str = Field(..., description="Comment text")
    created_by: Optional[str] = Field(None, description="Person who created the comment")
    created_date: Optional[datetime] = Field(None, description="Date when comment was created")
    modified_date: Optional[datetime] = Field(None, description="Date when comment was last modified")


class WorkItemUpdate(BaseModel):
    """Represents an update to a work item."""

    id: int = Field(..., description="Update ID")
    work_item_id: int = Field(..., description="Work item ID")
    revision: int = Field(..., description="Revision number")
    revised_by: Optional[str] = Field(None, description="Person who made the update")
    revised_date: Optional[datetime] = Field(None, description="Date of the update")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Fields that were changed")


class WorkItemRelation(BaseModel):
    """Represents a relation between work items."""

    rel: str = Field(..., description="Relation type")
    url: str = Field(..., description="URL of the related work item")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Relation attributes")


class UpdateWorkItemResult(BaseModel):
    """Result of updating a work item."""

    success: bool = Field(..., description="Whether the update was successful")
    work_item_id: int = Field(..., description="Work item ID")
    updated_fields: List[str] = Field(default_factory=list, description="List of fields that were updated")
    error_message: Optional[str] = Field(None, description="Error message if update failed")
