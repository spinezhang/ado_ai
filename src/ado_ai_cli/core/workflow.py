"""Main workflow orchestration for completing work items - Refactored for web compatibility."""

from typing import Optional, Callable, Dict, Any

from ado_ai_cli.ai.claude_client import AnalysisResult, ClaudeClient
from ado_ai_cli.azure_devops.client import AzureDevOpsClient
from ado_ai_cli.azure_devops.models import UpdateWorkItemResult, WorkItem
from ado_ai_cli.config import Settings
from ado_ai_cli.core.presenter import WorkflowPresenter
from ado_ai_cli.utils.exceptions import WorkflowError
from ado_ai_cli.utils.logger import get_logger

logger = get_logger()


class WorkflowResult:
    """Result of a workflow execution."""

    def __init__(
        self,
        success: bool,
        work_item_id: int,
        work_item: Optional[WorkItem] = None,
        analysis: Optional[AnalysisResult] = None,
        update_result: Optional[UpdateWorkItemResult] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.work_item_id = work_item_id
        self.work_item = work_item
        self.analysis = analysis
        self.update_result = update_result
        self.error_message = error_message


class WorkflowOrchestrator:
    """Orchestrates the complete workflow for work item completion."""

    def __init__(
        self,
        azure_client: AzureDevOpsClient,
        claude_client: ClaudeClient,
        settings: Settings,
        presenter: Optional[WorkflowPresenter] = None,
    ):
        """
        Initialize workflow orchestrator.

        Args:
            azure_client: Azure DevOps client
            claude_client: Claude AI client
            settings: Application settings
            presenter: Optional presenter for display (defaults to WorkflowPresenter for CLI)
        """
        self.azure_client = azure_client
        self.claude_client = claude_client
        self.settings = settings
        self.presenter = presenter or WorkflowPresenter()

    def fetch_work_item(
        self,
        work_item_id: int,
        display: bool = True
    ) -> WorkflowResult:
        """
        Fetch a work item and optionally display its details.

        Args:
            work_item_id: Work item ID to fetch
            display: Whether to display the work item (default True for CLI)

        Returns:
            WorkflowResult
        """
        try:
            logger.info(f"Fetching work item {work_item_id}")

            # Fetch work item
            work_item = self.azure_client.get_work_item(work_item_id)

            # Display work item (only if presenter is available and display=True)
            if display and self.presenter:
                self.presenter.display_work_item(work_item)

            return WorkflowResult(
                success=True,
                work_item_id=work_item_id,
                work_item=work_item,
            )

        except Exception as e:
            error_msg = f"Failed to fetch work item {work_item_id}: {str(e)}"
            logger.error(error_msg)
            return WorkflowResult(
                success=False,
                work_item_id=work_item_id,
                error_message=error_msg,
            )

    def complete_work_item(
        self,
        work_item_id: int,
        auto_approve: bool = False,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        display: bool = True,
        custom_prompt: Optional[str] = None,
    ) -> WorkflowResult:
        """
        Complete workflow: fetch, analyze, and optionally update a work item.

        Args:
            work_item_id: Work item ID to complete
            auto_approve: Skip confirmation prompt
            dry_run: Simulate without making changes
            progress_callback: Optional callback for progress updates
            display: Whether to display output (default True for CLI)
            custom_prompt: Optional custom instructions from user

        Returns:
            WorkflowResult
        """
        def emit_progress(step: str, data: Optional[Dict[str, Any]] = None):
            """Emit progress event to callback or display via presenter."""
            if progress_callback:
                progress_callback(step, data or {})
            elif display and self.presenter:
                self.presenter.print_step(step)

        try:
            logger.info(f"Starting workflow for work item {work_item_id}")

            # Step 1: Fetch work item
            emit_progress("fetching", {"work_item_id": work_item_id})
            work_item = self.azure_client.get_work_item(work_item_id)

            if display and self.presenter:
                self.presenter.display_work_item(work_item)

            # Step 2: Fetch recent comments
            emit_progress("fetching_comments", {"work_item_id": work_item_id})
            recent_comments = self.azure_client.get_comments(work_item_id, top=5)
            if recent_comments:
                logger.debug(f"Found {len(recent_comments)} recent comments")

            # Step 3: Analyze with Claude AI
            emit_progress("analyzing", {"work_item_id": work_item_id})
            analysis = self.claude_client.analyze_work_item(work_item, recent_comments, custom_prompt)

            # Display analysis
            if display and self.presenter:
                self.presenter.display_analysis(analysis, work_item, self.claude_client.model)

            # Step 4: Determine if update is needed
            if dry_run:
                emit_progress("dry_run_complete", {"work_item_id": work_item_id})
                if display and self.presenter:
                    self.presenter.print_warning("DRY RUN MODE: No changes will be made.")

                return WorkflowResult(
                    success=True,
                    work_item_id=work_item_id,
                    work_item=work_item,
                    analysis=analysis,
                )

            # Step 5: Get user confirmation (unless auto-approve)
            if not auto_approve and not self.settings.auto_approve:
                if display and self.presenter:
                    if not self.presenter.confirm_changes():
                        self.presenter.print_warning("Changes cancelled by user.")
                        return WorkflowResult(
                            success=False,
                            work_item_id=work_item_id,
                            work_item=work_item,
                            analysis=analysis,
                            error_message="User cancelled changes",
                        )
                else:
                    # In web mode, approval is handled separately
                    logger.info("Approval required but not in display mode")

            # Step 6: Update work item
            emit_progress("updating", {"work_item_id": work_item_id})
            update_fields = self._build_update_fields(work_item, analysis)

            update_result = self.azure_client.update_work_item(
                work_item_id=work_item_id,
                fields=update_fields,
                comment=self._format_ai_comment(analysis),
            )

            if update_result.success:
                emit_progress("completed", {"work_item_id": work_item_id})
                if display and self.presenter:
                    self.presenter.print_success(f"Work item {work_item_id} updated successfully!")
                    if work_item.url:
                        self.presenter.print_step(f"View at: {work_item.url}")

                return WorkflowResult(
                    success=True,
                    work_item_id=work_item_id,
                    work_item=work_item,
                    analysis=analysis,
                    update_result=update_result,
                )
            else:
                emit_progress("failed", {"work_item_id": work_item_id, "error": update_result.error_message})
                if display and self.presenter:
                    self.presenter.print_error(f"Failed to update work item: {update_result.error_message}")

                return WorkflowResult(
                    success=False,
                    work_item_id=work_item_id,
                    work_item=work_item,
                    analysis=analysis,
                    update_result=update_result,
                    error_message=update_result.error_message,
                )

        except Exception as e:
            error_msg = f"Workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            emit_progress("error", {"work_item_id": work_item_id, "error": error_msg})

            if display and self.presenter:
                self.presenter.print_error(f"Error: {error_msg}")

            return WorkflowResult(
                success=False,
                work_item_id=work_item_id,
                error_message=error_msg,
            )

    def _build_update_fields(self, work_item: WorkItem, analysis: AnalysisResult) -> dict:
        """Build dictionary of fields to update."""
        fields = {}

        # Update status if changed
        if analysis.suggested_status and analysis.suggested_status != work_item.state:
            fields["System.State"] = analysis.suggested_status

        # Update remaining work
        if analysis.suggested_remaining_work != work_item.remaining_work:
            fields["Microsoft.VSTS.Scheduling.RemainingWork"] = analysis.suggested_remaining_work

        # Add AI-completed tag if not already present
        existing_tags = work_item.tags.split(";") if work_item.tags else []
        if "AI-Completed" not in existing_tags:
            existing_tags.append("AI-Completed")
            fields["System.Tags"] = ";".join(existing_tags)

        return fields

    def _format_ai_comment(self, analysis: AnalysisResult) -> str:
        """Format AI analysis as a comment."""
        comment = f"""🤖 AI Analysis

{analysis.comment}

---
*Generated by Claude AI*
"""
        return comment
