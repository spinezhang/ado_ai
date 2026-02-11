"""Main workflow orchestration for completing work items."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ado_ai_cli.ai.claude_client import AnalysisResult, ClaudeClient
from ado_ai_cli.azure_devops.client import AzureDevOpsClient
from ado_ai_cli.azure_devops.models import UpdateWorkItemResult, WorkItem
from ado_ai_cli.config import Settings
from ado_ai_cli.utils.exceptions import WorkflowError
from ado_ai_cli.utils.logger import get_logger

logger = get_logger()
console = Console()


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
    ):
        """
        Initialize workflow orchestrator.

        Args:
            azure_client: Azure DevOps client
            claude_client: Claude AI client
            settings: Application settings
        """
        self.azure_client = azure_client
        self.claude_client = claude_client
        self.settings = settings

    def fetch_work_item(self, work_item_id: int) -> WorkflowResult:
        """
        Fetch a work item and display its details.

        Args:
            work_item_id: Work item ID to fetch

        Returns:
            WorkflowResult
        """
        try:
            logger.info(f"Fetching work item {work_item_id}")

            # Fetch work item
            work_item = self.azure_client.get_work_item(work_item_id)

            # Display work item
            self._display_work_item(work_item)

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
        self, work_item_id: int, auto_approve: bool = False, dry_run: bool = False
    ) -> WorkflowResult:
        """
        Complete workflow: fetch, analyze, and optionally update a work item.

        Args:
            work_item_id: Work item ID to complete
            auto_approve: Skip confirmation prompt
            dry_run: Simulate without making changes

        Returns:
            WorkflowResult
        """
        try:
            logger.info(f"Starting workflow for work item {work_item_id}")

            # Step 1: Fetch work item
            console.print(f"[bold blue]✓[/bold blue] Fetching work item {work_item_id}...")
            work_item = self.azure_client.get_work_item(work_item_id)
            self._display_work_item(work_item)

            # Step 2: Fetch recent comments
            console.print("\n[bold blue]✓[/bold blue] Fetching recent comments...")
            recent_comments = self.azure_client.get_comments(work_item_id, top=5)
            if recent_comments:
                logger.debug(f"Found {len(recent_comments)} recent comments")

            # Step 3: Analyze with Claude AI
            console.print("\n[bold blue]✓[/bold blue] Analyzing with Claude AI...")
            with console.status("[bold green]Analyzing work item...", spinner="dots"):
                analysis = self.claude_client.analyze_work_item(work_item, recent_comments)

            # Display analysis
            self._display_analysis(analysis, work_item)

            # Step 4: Determine if update is needed
            if dry_run:
                console.print("\n[bold yellow]DRY RUN MODE:[/bold yellow] No changes will be made.")
                return WorkflowResult(
                    success=True,
                    work_item_id=work_item_id,
                    work_item=work_item,
                    analysis=analysis,
                )

            # Step 5: Get user confirmation (unless auto-approve)
            if not auto_approve and not self.settings.auto_approve:
                console.print()
                if not self._confirm_changes():
                    console.print("[yellow]Changes cancelled by user.[/yellow]")
                    return WorkflowResult(
                        success=False,
                        work_item_id=work_item_id,
                        work_item=work_item,
                        analysis=analysis,
                        error_message="User cancelled changes",
                    )

            # Step 6: Update work item
            console.print("\n[bold blue]✓[/bold blue] Updating work item...")
            update_fields = self._build_update_fields(work_item, analysis)

            update_result = self.azure_client.update_work_item(
                work_item_id=work_item_id,
                fields=update_fields,
                comment=self._format_ai_comment(analysis),
            )

            if update_result.success:
                console.print(
                    f"\n[bold green]✓ Work item {work_item_id} updated successfully![/bold green]"
                )
                if work_item.url:
                    console.print(f"View at: [link]{work_item.url}[/link]")

                return WorkflowResult(
                    success=True,
                    work_item_id=work_item_id,
                    work_item=work_item,
                    analysis=analysis,
                    update_result=update_result,
                )
            else:
                console.print(
                    f"\n[bold red]✗ Failed to update work item:[/bold red] {update_result.error_message}"
                )
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
            console.print(f"\n[bold red]✗ Error:[/bold red] {error_msg}")
            return WorkflowResult(
                success=False,
                work_item_id=work_item_id,
                error_message=error_msg,
            )

    def _display_work_item(self, work_item: WorkItem) -> None:
        """Display work item details in a formatted table."""
        table = Table(title="Work Item Details", show_header=False, box=None)
        table.add_column("Field", style="bold cyan", width=15)
        table.add_column("Value", style="white")

        table.add_row("ID", str(work_item.id))
        table.add_row("Type", work_item.work_item_type)
        table.add_row("Title", work_item.title)
        table.add_row("State", f"[yellow]{work_item.state}[/yellow]")

        if work_item.assigned_to:
            table.add_row("Assigned To", work_item.assigned_to)

        if work_item.priority:
            table.add_row("Priority", str(work_item.priority))

        if work_item.remaining_work is not None:
            table.add_row("Remaining Work", f"{work_item.remaining_work} hours")

        if work_item.tags:
            table.add_row("Tags", work_item.tags)

        console.print(table)

        if work_item.description:
            console.print(
                Panel(
                    work_item.description[:500] + ("..." if len(work_item.description) > 500 else ""),
                    title="Description",
                    border_style="blue",
                )
            )

    def _display_analysis(self, analysis: AnalysisResult, work_item: WorkItem) -> None:
        """Display AI analysis results."""
        console.print("\n[bold cyan]🤖 AI Analysis[/bold cyan]")
        console.print("━" * 60)

        console.print(f"\n[bold]Analysis:[/bold]\n{analysis.analysis}")
        console.print(f"\n[bold]Solution:[/bold]\n{analysis.solution}")

        if analysis.tasks:
            console.print("\n[bold]Tasks:[/bold]")
            for idx, task in enumerate(analysis.tasks, 1):
                console.print(f"  {idx}. {task}")

        if analysis.risks:
            console.print("\n[bold yellow]⚠️  Risks & Considerations:[/bold yellow]")
            for idx, risk in enumerate(analysis.risks, 1):
                console.print(f"  {idx}. {risk}")

        console.print("\n[bold cyan]💡 Proposed Changes:[/bold cyan]")
        if analysis.suggested_status != work_item.state:
            console.print(f"  • Status: [yellow]{work_item.state}[/yellow] → [green]{analysis.suggested_status}[/green]")
        if analysis.suggested_remaining_work != work_item.remaining_work:
            console.print(f"  • Remaining Work: {work_item.remaining_work} → {analysis.suggested_remaining_work} hours")
        console.print("  • Add AI-generated comment")

        # Display cost
        cost = analysis.token_usage.calculate_cost(self.claude_client.model)
        console.print(
            f"\n[bold]💰 Cost:[/bold] ${cost:.4f} "
            f"({analysis.token_usage.input_tokens:,} input, {analysis.token_usage.output_tokens:,} output tokens)"
        )

    def _confirm_changes(self) -> bool:
        """Prompt user to confirm changes."""
        response = console.input("\n[bold]Apply these changes?[/bold] [cyan](y/n)[/cyan]: ")
        return response.lower() in ("y", "yes")

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
