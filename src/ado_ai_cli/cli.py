"""CLI interface for ADO AI tool."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ado_ai_cli.ai.claude_client import ClaudeClient
from ado_ai_cli.azure_devops.client import AzureDevOpsClient
from ado_ai_cli.config import get_settings, Settings
from ado_ai_cli.core.workflow import WorkflowOrchestrator
from ado_ai_cli.utils.exceptions import (
    AdoAiError,
    AuthenticationError,
    ConfigurationError,
)
from ado_ai_cli.utils.logger import setup_logger, get_logger

app = typer.Typer(
    name="ado-ai",
    help="Azure DevOps AI Auto-Complete CLI Tool powered by Claude",
    add_completion=False,
)
console = Console()


# Global options
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Show only warnings and errors"),
):
    """Azure DevOps AI Auto-Complete CLI Tool."""
    # Configure logging based on flags
    if verbose:
        log_level = "DEBUG"
    elif quiet:
        log_level = "WARNING"
    else:
        log_level = "INFO"

    setup_logger(log_level=log_level, enable_file_logging=True)


@app.command()
def fetch(
    work_item_id: int = typer.Argument(..., help="Work item ID to fetch"),
):
    """Fetch and display a work item."""
    logger = get_logger()

    try:
        # Load settings
        settings = get_settings()

        # Initialize clients
        azure_client = AzureDevOpsClient(settings)
        claude_client = ClaudeClient(settings)

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(azure_client, claude_client, settings)

        # Execute fetch
        result = orchestrator.fetch_work_item(work_item_id)

        if result.success:
            if result.work_item and result.work_item.url:
                console.print(f"\n[bold]URL:[/bold] {result.work_item.url}")
            sys.exit(0)
        else:
            console.print(f"[bold red]Error:[/bold red] {result.error_message}")
            sys.exit(1)

    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {str(e)}")
        console.print("\n[yellow]Hint:[/yellow] Make sure you have created a .env file with all required settings.")
        console.print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    except AuthenticationError as e:
        console.print(f"[bold red]Authentication Error:[/bold red] {str(e)}")
        console.print("\n[yellow]Hint:[/yellow] Check that your Azure DevOps PAT and Anthropic API key are valid.")
        sys.exit(1)
    except AdoAiError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        console.print(f"[bold red]Unexpected Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def complete(
    work_item_id: int = typer.Argument(..., help="Work item ID to complete"),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve",
        "-y",
        help="Skip confirmation prompt and apply changes automatically",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate the workflow without making actual changes",
    ),
):
    """Auto-complete a work item using AI analysis."""
    logger = get_logger()

    try:
        # Load settings
        settings = get_settings()

        # Override auto_approve if set via flag
        if auto_approve:
            settings.auto_approve = True

        # Override dry_run if set via flag
        if dry_run:
            settings.dry_run = True

        # Initialize clients
        azure_client = AzureDevOpsClient(settings)
        claude_client = ClaudeClient(settings)

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(azure_client, claude_client, settings)

        # Execute workflow
        result = orchestrator.complete_work_item(
            work_item_id=work_item_id,
            auto_approve=auto_approve,
            dry_run=dry_run,
        )

        if result.success:
            sys.exit(0)
        else:
            if result.error_message and "cancelled" not in result.error_message.lower():
                console.print(f"[bold red]Error:[/bold red] {result.error_message}")
            sys.exit(1)

    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {str(e)}")
        console.print("\n[yellow]Hint:[/yellow] Make sure you have created a .env file with all required settings.")
        console.print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    except AuthenticationError as e:
        console.print(f"[bold red]Authentication Error:[/bold red] {str(e)}")
        console.print("\n[yellow]Hint:[/yellow] Check that your Azure DevOps PAT and Anthropic API key are valid.")
        sys.exit(1)
    except AdoAiError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        console.print(f"[bold red]Unexpected Error:[/bold red] {str(e)}")
        sys.exit(1)


# Config command group
config_app = typer.Typer(help="Configuration management commands")
app.add_typer(config_app, name="config")


@config_app.command("validate")
def config_validate():
    """Validate configuration settings."""
    try:
        settings = get_settings()
        console.print("[bold green]✓ Configuration is valid![/bold green]")

        # Display non-sensitive settings
        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Setting", style="cyan", width=30)
        table.add_column("Value", style="white")

        table.add_row("Azure DevOps Org", settings.org_url_str)
        table.add_row("Azure DevOps Project", settings.azure_devops_project)
        table.add_row("Azure DevOps PAT", "***REDACTED***")
        table.add_row("Anthropic API Key", "***REDACTED***")
        table.add_row("Claude Model", settings.claude_model)
        table.add_row("Log Level", settings.log_level)
        table.add_row("Auto Approve", str(settings.auto_approve))
        table.add_row("Max Retries", str(settings.max_retries))
        table.add_row("Timeout (seconds)", str(settings.timeout_seconds))

        console.print(table)
        sys.exit(0)

    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@config_app.command("show")
def config_show():
    """Show current configuration (same as validate)."""
    config_validate()


@app.command()
def version():
    """Show version information."""
    console.print("[bold]ADO AI CLI[/bold] - Azure DevOps AI Auto-Complete Tool")
    console.print("Version: 0.1.0")
    console.print("Powered by Claude AI")
    sys.exit(0)


if __name__ == "__main__":
    app()
