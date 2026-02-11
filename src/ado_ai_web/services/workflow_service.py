"""Workflow service wrapper for web interface."""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import re

from ado_ai_cli.core.workflow import WorkflowOrchestrator, WorkflowResult
from ado_ai_cli.azure_devops.client import AzureDevOpsClient
from ado_ai_cli.ai.claude_client import ClaudeClient
from ado_ai_cli.config import Settings as CliSettings

from ado_ai_web.models.database import WorkItemHistory, User
from ado_ai_web.services.settings_manager import SettingsManager


class WorkflowService:
    """
    Service layer wrapping WorkflowOrchestrator for web use.

    Handles:
    - Loading credentials from database
    - Initializing clients
    - Progress tracking
    - Database logging
    - Response formatting
    """

    def __init__(self, db: Session):
        """
        Initialize workflow service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.settings_manager = SettingsManager(db)

    def _get_orchestrator(self, user_id: int) -> WorkflowOrchestrator:
        """
        Create orchestrator instance with user's credentials.

        Args:
            user_id: User ID

        Returns:
            WorkflowOrchestrator instance

        Raises:
            ValueError: If credentials not found or invalid
        """
        # Get decrypted credentials
        creds = self.settings_manager.get_decrypted_credentials(user_id)
        if not creds:
            raise ValueError("Credentials not found")

        # Create CLI settings
        cli_settings = CliSettings(
            azure_devops_org_url=creds["azure_devops_org_url"],
            azure_devops_project=creds["azure_devops_project"],
            azure_devops_pat=creds["azure_devops_pat"],
            anthropic_api_key=creds["anthropic_api_key"],
            claude_model=creds["claude_model"],
            auto_approve=creds["auto_approve"],
            max_tokens=creds["max_tokens"],
            temperature=creds["temperature"],
        )

        # Initialize clients
        azure_client = AzureDevOpsClient(cli_settings)
        claude_client = ClaudeClient(cli_settings)

        # Create orchestrator (no presenter for web mode)
        orchestrator = WorkflowOrchestrator(
            azure_client=azure_client,
            claude_client=claude_client,
            settings=cli_settings,
            presenter=None,  # No CLI display in web mode
        )

        return orchestrator

    def fetch_work_item(self, user_id: int, work_item_id: int) -> Dict[str, Any]:
        """
        Fetch work item details including comments.

        Args:
            user_id: User ID
            work_item_id: Work item ID

        Returns:
            Dictionary with work item data and comments

        Raises:
            Exception: If fetch fails
        """
        orchestrator = self._get_orchestrator(user_id)
        result = orchestrator.fetch_work_item(work_item_id, display=False)

        if not result.success:
            raise Exception(result.error_message or "Failed to fetch work item")

        # Fetch comments
        comments = orchestrator.azure_client.get_comments(work_item_id, top=10)
        comments_data = []
        if comments:
            for comment in comments:
                # Strip HTML tags from comment text
                clean_text = re.sub(r'<[^>]+>', '', comment.text) if comment.text else ''
                comments_data.append({
                    "id": comment.id,
                    "text": clean_text,
                    "created_by": comment.created_by,
                    "created_date": comment.created_date.isoformat() if comment.created_date else None,
                    "modified_date": comment.modified_date.isoformat() if comment.modified_date else None,
                })

        # Convert to dictionary
        work_item = result.work_item

        # Strip HTML tags from description
        clean_description = re.sub(r'<[^>]+>', '', work_item.description) if work_item.description else ''

        return {
            "work_item_id": work_item.id,
            "work_item_type": work_item.work_item_type,
            "title": work_item.title,
            "state": work_item.state,
            "description": clean_description,
            "assigned_to": work_item.assigned_to,
            "priority": work_item.priority,
            "remaining_work": work_item.remaining_work,
            "tags": work_item.tags,
            "url": work_item.url,
            "comments": comments_data,
        }

    def analyze_work_item(
        self,
        user_id: int,
        work_item_id: int,
        custom_prompt: Optional[str] = None,
        work_folder_path: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> int:
        """
        Analyze work item with AI (async operation).

        Creates WorkItemHistory record and starts analysis.

        Args:
            user_id: User ID
            work_item_id: Work item ID
            custom_prompt: Optional custom prompt
            work_folder_path: Optional work folder path for file operations
            progress_callback: Optional progress callback

        Returns:
            WorkItemHistory ID for tracking

        Raises:
            Exception: If analysis fails
        """
        # Create history record
        history = WorkItemHistory(
            user_id=user_id,
            work_item_id=work_item_id,
            custom_prompt=custom_prompt,
            work_folder_path=work_folder_path,
            status="analyzing",
            created_at=datetime.utcnow(),
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        try:
            # Get orchestrator
            orchestrator = self._get_orchestrator(user_id)

            # Create progress callback that updates database
            def db_progress_callback(step: str, data: Dict[str, Any]):
                if progress_callback:
                    progress_callback(step, data)

                # Log progress (optional - could update history record)
                # For now, just pass through to provided callback

            # Run analysis (dry_run=True means analysis-only, no updates)
            result = orchestrator.complete_work_item(
                work_item_id=work_item_id,
                auto_approve=False,
                dry_run=True,  # Analysis-only mode for web - no work item updates
                progress_callback=db_progress_callback,
                display=False,
                custom_prompt=custom_prompt,
            )

            if result.success:
                # Update history with analysis results
                history.work_item_type = result.work_item.work_item_type if result.work_item else None
                history.title = result.work_item.title if result.work_item else None
                history.status = "completed"
                history.completed_at = datetime.utcnow()

                if result.analysis:
                    # Store analysis as JSON
                    history.analysis_result = {
                        "analysis": result.analysis.analysis,
                        "solution": result.analysis.solution,
                        "tasks": result.analysis.tasks,
                        "risks": result.analysis.risks,
                        "suggested_status": result.analysis.suggested_status,
                        "suggested_remaining_work": result.analysis.suggested_remaining_work,
                        "comment": result.analysis.comment,
                        "file_changes": result.analysis.file_changes,
                    }

                    # Store token usage
                    history.token_usage = {
                        "input_tokens": result.analysis.token_usage.input_tokens,
                        "output_tokens": result.analysis.token_usage.output_tokens,
                    }

                    # Calculate cost
                    creds = self.settings_manager.get_decrypted_credentials(user_id)
                    model = creds.get("claude_model", "claude-opus-4-6")
                    history.cost = result.analysis.token_usage.calculate_cost(model)

            else:
                history.status = "failed"
                history.error_message = result.error_message
                history.completed_at = datetime.utcnow()

            self.db.commit()
            return history.id

        except Exception as e:
            # Update history with error
            history.status = "failed"
            history.error_message = str(e)
            history.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    def get_analysis_result(self, history_id: int) -> Optional[Dict[str, Any]]:
        """
        Get analysis result by history ID.

        Args:
            history_id: WorkItemHistory ID

        Returns:
            Dictionary with analysis data or None
        """
        history = self.db.query(WorkItemHistory).filter(WorkItemHistory.id == history_id).first()
        if not history:
            return None

        return {
            "id": history.id,
            "work_item_id": history.work_item_id,
            "work_item_type": history.work_item_type,
            "title": history.title,
            "status": history.status,
            "analysis_result": history.analysis_result,
            "token_usage": history.token_usage,
            "cost": history.cost,
            "custom_prompt": history.custom_prompt,
            "error_message": history.error_message,
            "created_at": history.created_at.isoformat() if history.created_at else None,
            "completed_at": history.completed_at.isoformat() if history.completed_at else None,
        }

    def apply_changes(
        self,
        user_id: int,
        work_item_id: int,
        modified_analysis: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apply changes to work item (after user approval).

        Args:
            user_id: User ID
            work_item_id: Work item ID
            modified_analysis: Optional user-modified analysis fields

        Returns:
            True if successful

        Raises:
            Exception: If update fails
        """
        # TODO: Implement actual update logic
        # This would need to:
        # 1. Get the analysis from history
        # 2. Apply any user modifications
        # 3. Call orchestrator to update work item
        # 4. Return result

        # For now, just a placeholder
        raise NotImplementedError("Apply changes not yet implemented")
