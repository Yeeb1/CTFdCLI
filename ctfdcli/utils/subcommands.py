"""Utility functions for displaying subcommands."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def show_subcommands(command_name: str, subcommands: list, description: str = None):
    """Display available subcommands for a command.

    Args:
        command_name: Name of the parent command
        subcommands: List of tuples (subcommand, description)
        description: Optional description of the parent command
    """

    # Header
    header_text = f"🚩 {command_name.title()} - Available Subcommands"
    if description:
        header_text = f"{header_text}\n{description}"

    header = Text(header_text, style="bold cyan")
    header_panel = Panel(header, border_style="cyan")
    console.print(header_panel)

    # Subcommands table
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Subcommand", style="cyan", min_width=15)
    table.add_column("Description", style="white")

    for subcmd, desc in subcommands:
        table.add_row(subcmd, desc)

    console.print(table)

    # Usage examples
    examples = []
    for subcmd, _ in subcommands[:3]:  # Show first 3 as examples
        examples.append(f"[cyan]ctfdcli {command_name} {subcmd}[/cyan]")

    if examples:
        examples_panel = Panel(
            "\n".join(examples),
            title="🚀 Examples",
            border_style="green"
        )
        console.print(examples_panel)

    # Tip
    tip = Panel(
        f"[yellow]💡 Tip:[/yellow] Use [cyan]ctfdcli {command_name} <subcommand> --help[/cyan] for detailed help",
        border_style="yellow"
    )
    console.print(tip)