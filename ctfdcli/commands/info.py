"""CTF information display commands."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from datetime import datetime
from typing import Optional

from ..core import ConfigManager, CTFdClient

app = typer.Typer(help="Display CTF information")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Display comprehensive CTF information including description, rules, and settings."""

    if ctx.invoked_subcommand is not None:
        return

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Fetching CTF information from {profile_obj.url}...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get comprehensive CTF info
        ctf_info = client.get_ctf_info()

        # Display the information
        _display_ctf_info(ctf_info, str(profile_obj.url), client)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch CTF information: {e}[/red]")
        raise typer.Exit(1)


def _display_ctf_info(ctf_info, url: str, client=None):
    """Display comprehensive CTF information in a beautiful layout."""

    # Main CTF Header
    header_text = Text(f"🚩 {ctf_info.name}", style="bold cyan")
    header_panel = Panel(
        header_text,
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(header_panel)

    # Basic Information Panel
    basic_info = []
    basic_info.append(f"[bold cyan]URL:[/bold cyan] {url}")

    if ctf_info.description:
        basic_info.append(f"[bold cyan]Description:[/bold cyan] {ctf_info.description}")

    mode_display = "👥 Teams" if ctf_info.mode == "teams" else "👤 Individual"
    basic_info.append(f"[bold cyan]Mode:[/bold cyan] {mode_display}")

    if ctf_info.theme:
        basic_info.append(f"[bold cyan]Theme:[/bold cyan] {ctf_info.theme}")

    basic_panel = Panel(
        "\n".join(basic_info),
        title="📋 Basic Information",
        border_style="blue",
        padding=(1, 2)
    )

    # Timeline Panel
    timeline_info = []
    now = datetime.now()

    if ctf_info.start:
        status = "🟢 Started" if ctf_info.start <= now else "🔵 Upcoming"
        timeline_info.append(f"[bold cyan]Start:[/bold cyan] {ctf_info.start.strftime('%Y-%m-%d %H:%M:%S UTC')} {status}")

    if ctf_info.end:
        status = "🔴 Ended" if ctf_info.end <= now else "🟡 Ongoing" if ctf_info.start and ctf_info.start <= now else "⚪ Upcoming"
        timeline_info.append(f"[bold cyan]End:[/bold cyan] {ctf_info.end.strftime('%Y-%m-%d %H:%M:%S UTC')} {status}")

    if ctf_info.freeze:
        status = "🥶 Frozen" if ctf_info.freeze <= now else "❄️ Freeze Pending"
        timeline_info.append(f"[bold cyan]Freeze:[/bold cyan] {ctf_info.freeze.strftime('%Y-%m-%d %H:%M:%S UTC')} {status}")

    if not timeline_info:
        timeline_info.append("[yellow]No timeline information available[/yellow]")

    timeline_panel = Panel(
        "\n".join(timeline_info),
        title="⏰ Timeline",
        border_style="yellow",
        padding=(1, 2)
    )

    # Settings Panel
    settings_info = []

    registration_status = "✅ Open" if ctf_info.registration else "❌ Closed"
    settings_info.append(f"[bold cyan]Registration:[/bold cyan] {registration_status}")

    if ctf_info.max_team_size:
        settings_info.append(f"[bold cyan]Max Team Size:[/bold cyan] {ctf_info.max_team_size}")

    verification_status = "✅ Required" if ctf_info.verification_required else "❌ Not Required"
    settings_info.append(f"[bold cyan]Email Verification:[/bold cyan] {verification_status}")

    workshop_status = "✅ Yes" if ctf_info.workshop_mode else "❌ No"
    settings_info.append(f"[bold cyan]Workshop Mode:[/bold cyan] {workshop_status}")

    paused_status = "🛑 Paused" if ctf_info.paused else "▶️ Active"
    settings_info.append(f"[bold cyan]Status:[/bold cyan] {paused_status}")

    settings_panel = Panel(
        "\n".join(settings_info),
        title="⚙️ Settings",
        border_style="green",
        padding=(1, 2)
    )

    # Display panels in columns
    console.print(Columns([basic_panel, timeline_panel, settings_panel], equal=True, expand=True))

    # Rules Panel (full width if available)
    if ctf_info.rules:
        # Clean up HTML tags from rules if present
        import re
        clean_rules = re.sub(r'<[^>]+>', '', ctf_info.rules)
        clean_rules = clean_rules.strip()

        if clean_rules:
            rules_panel = Panel(
                clean_rules,
                title="📜 Rules & Guidelines",
                border_style="red",
                padding=(1, 2)
            )
            console.print(rules_panel)

    # Statistics summary
    try:
        # Get additional statistics
        challenges = client.get_challenges()
        scoreboard = client.get_scoreboard(10)

        stats_info = []
        stats_info.append(f"[bold cyan]Total Challenges:[/bold cyan] {len(challenges)}")

        if challenges:
            categories = set(c.category for c in challenges)
            stats_info.append(f"[bold cyan]Categories:[/bold cyan] {len(categories)}")

            solved = [c for c in challenges if c.solved_by_me]
            if solved:
                stats_info.append(f"[bold cyan]Your Solved:[/bold cyan] {len(solved)}/{len(challenges)} ({len(solved)/len(challenges)*100:.1f}%)")

        if scoreboard:
            stats_info.append(f"[bold cyan]Total Participants:[/bold cyan] {len(scoreboard)}")
            if len(scoreboard) >= 10:
                stats_info.append("[dim]Top 10 shown[/dim]")

        if stats_info:
            stats_panel = Panel(
                "\n".join(stats_info),
                title="📊 Statistics",
                border_style="magenta",
                padding=(1, 2)
            )
            console.print(stats_panel)

    except Exception:
        # If we can't get statistics, that's okay
        pass


@app.command("summary")
def summary_info(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Display a compact summary of CTF information."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        ctf_info = client.get_ctf_info()

        # Create compact summary table
        table = Table(title=f"📋 {ctf_info.name} - Summary", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", ctf_info.name)
        table.add_row("URL", str(profile_obj.url))
        table.add_row("Mode", "👥 Teams" if ctf_info.mode == "teams" else "👤 Individual")

        if ctf_info.start:
            table.add_row("Start", ctf_info.start.strftime('%Y-%m-%d %H:%M UTC'))
        if ctf_info.end:
            table.add_row("End", ctf_info.end.strftime('%Y-%m-%d %H:%M UTC'))

        table.add_row("Registration", "✅ Open" if ctf_info.registration else "❌ Closed")
        table.add_row("Status", "🛑 Paused" if ctf_info.paused else "▶️ Active")

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch CTF summary: {e}[/red]")
        raise typer.Exit(1)