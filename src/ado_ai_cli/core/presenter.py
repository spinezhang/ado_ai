"""Presentation layer for workflow output - separated from business logic."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ado_ai_cli.ai.claude_client import AnalysisResult
from ado_ai_cli.azure_devops.models import WorkItem

console = Console()


class WorkflowPresenter:
    """
    Handles display/presentation logic for workflow operations.

    Separates display concerns from business logic in WorkflowOrchestrator,
    making it easier to use the orchestrator in non-CLI contexts (e.g., web service).
    """

    @staticmethod
    def display_work_item(work_item: WorkItem) -> None:
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

    @staticmethod
    def display_analysis(analysis: AnalysisResult, work_item: WorkItem, model: str) -> None:
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
        cost = analysis.token_usage.calculate_cost(model)
        console.print(
            f"\n[bold]💰 Cost:[/bold] ${cost:.4f} "
            f"({analysis.token_usage.input_tokens:,} input, {analysis.token_usage.output_tokens:,} output tokens)"
        )

    @staticmethod
    def confirm_changes() -> bool:
        """Prompt user to confirm changes."""
        response = console.input("\n[bold]Apply these changes?[/bold] [cyan](y/n)[/cyan]: ")
        return response.lower() in ("y", "yes")

    @staticmethod
    def print_step(message: str) -> None:
        """Print a workflow step message."""
        console.print(f"[bold blue]✓[/bold blue] {message}")

    @staticmethod
    def print_success(message: str) -> None:
        """Print a success message."""
        console.print(f"\n[bold green]✓ {message}[/bold green]")

    @staticmethod
    def print_error(message: str) -> None:
        """Print an error message."""
        console.print(f"\n[bold red]✗ {message}[/bold red]")

    @staticmethod
    def print_warning(message: str) -> None:
        """Print a warning message."""
        console.print(f"[bold yellow]{message}[/bold yellow]")
