"""Main CLI application entry point."""

import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns

from .commands import challenges, cwd, init, info, lookup, profile, scoreboard, submit, sync, team

console = Console()

def show_available_commands():
    """Display available commands in a nice format."""

    # Header
    header = Text("🚩 CTFd CLI - Available Commands", style="bold cyan")
    header_panel = Panel(header, border_style="cyan")
    console.print(header_panel)

    # Commands table
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Command", style="cyan", min_width=12)
    table.add_column("Description", style="white")

    commands = [
        ("init", "🔧 Initialize CTF profile configuration"),
        ("profile", "👤 Manage CTF profiles (list, show, test, delete)"),
        ("info", "ℹ️ Display CTF information (description, rules, timeline)"),
        ("lookup", "🔍 Lookup remote teams and users information"),
        ("team", "👥 View team information (info, members, stats)"),
        ("challenges", "🚩 List and manage challenges (list, show, solved, categories)"),
        ("sync", "📥 Sync challenges and files to local directory"),
        ("cwd", "📂 Work within challenge directories (info, submit)"),
        ("submit", "📝 Submit flags (single, bulk, view history)"),
        ("scoreboard", "🏆 View scoreboard (compact, detailed, stats)"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)

    # Quick start examples
    examples = [
        "[cyan]ctfdcli init[/cyan] - Set up your first profile",
        "[cyan]ctfdcli challenges list[/cyan] - View all challenges",
        "[cyan]ctfdcli scoreboard[/cyan] - Check current standings",
        "[cyan]ctfdcli submit 1 flag{...}[/cyan] - Submit a flag"
    ]

    examples_panel = Panel(
        "\n".join(examples),
        title="🚀 Quick Start Examples",
        border_style="green"
    )
    console.print(examples_panel)

    # Tip
    tip = Panel(
        "[yellow]💡 Tip:[/yellow] Use [cyan]ctfdcli <command> --help[/cyan] for detailed help on any command",
        border_style="yellow"
    )
    console.print(tip)

app = typer.Typer(
    name="ctfdcli",
    help="🚩 A comprehensive CLI tool for CTFd platforms",
    rich_markup_mode="rich",
    no_args_is_help=False,  # Don't automatically show help when no args
)

# Add command groups
app.add_typer(init.app, name="init", help="Initialize CTF profile configuration")
app.add_typer(profile.app, name="profile", help="Manage CTF profiles")
app.add_typer(info.app, name="info", help="Display CTF information")
app.add_typer(lookup.app, name="lookup", help="Lookup remote teams and users")
app.add_typer(team.app, name="team", help="View team information")
app.add_typer(challenges.app, name="challenges", help="List and manage challenges")
app.add_typer(sync.app, name="sync", help="Sync challenges and files")
app.add_typer(cwd.app, name="cwd", help="Work within challenge directories")
app.add_typer(submit.app, name="submit", help="Submit flags")
app.add_typer(scoreboard.app, name="scoreboard", help="View scoreboard")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """CTFd CLI - Your ultimate CTF companion! 🚩"""
    if ctx.invoked_subcommand is None:
        # No command provided, show available commands
        show_available_commands()




if __name__ == "__main__":
    app()