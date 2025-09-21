"""Scoreboard display commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from typing import Optional

from ..core import ConfigManager, CTFdClient
from ..utils import show_subcommands

app = typer.Typer(help="View scoreboard")
console = Console()


def get_rank_style(position: int) -> str:
    """Get style for rank display.

    Args:
        position: Rank position

    Returns:
        Rich style string
    """
    if position == 1:
        return "gold1"
    elif position == 2:
        return "bright_white"
    elif position == 3:
        return "orange3"
    elif position <= 10:
        return "green"
    else:
        return "cyan"


def get_rank_emoji(position: int) -> str:
    """Get emoji for rank position.

    Args:
        position: Rank position

    Returns:
        Emoji string
    """
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    elif position <= 10:
        return "🏆"
    else:
        return "📊"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    count: int = typer.Option(50, "--count", "-c", help="Number of entries to show"),
    me: bool = typer.Option(False, "--me", "-m", help="Highlight current user"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed scoreboard")
):
    """Display the CTF scoreboard."""
    if ctx.invoked_subcommand is None:
        # Show the main scoreboard when no subcommand is provided
        show_scoreboard(profile=profile, count=count, me=me, detailed=detailed)


def show_scoreboard(
    profile: str = None,
    count: int = 50,
    me: bool = False,
    detailed: bool = False
):
    """Display the CTF scoreboard."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Fetching scoreboard from {profile_obj.url}...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get CTF info and current user (gracefully handle failures)
        try:
            ctf_info = client.get_ctf_info()
        except Exception:
            from ..core.models import CTFInfo
            ctf_info = CTFInfo(name="CTF", mode="users")

        # Get current user/team info for highlighting
        current_user = None
        current_team = None
        try:
            current_user = client.get_me()
        except Exception:
            pass  # Ignore if we can't get user info

        # Also try to get team info for team mode
        try:
            team_data = client._make_request('GET', '/teams/me')
            if team_data:
                current_team = team_data
        except Exception:
            pass  # Ignore if we can't get team info

        # Get scoreboard
        scoreboard = client.get_scoreboard(count)

        if not scoreboard:
            console.print("[yellow]No scoreboard data available[/yellow]")
            return

        if detailed:
            _display_detailed_scoreboard(scoreboard, ctf_info, current_user, current_team, limit=count)
        else:
            _display_compact_scoreboard(scoreboard, ctf_info, current_user, current_team)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch scoreboard: {e}[/red]")
        raise typer.Exit(1)


def _display_compact_scoreboard(scoreboard, ctf_info, current_user, current_team):
    """Display compact scoreboard table."""
    table = Table(
        title=f"🏆 {ctf_info.name} - Scoreboard",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Rank", style="yellow", width=8)
    table.add_column("Team/User", style="cyan", min_width=20)
    table.add_column("Score", style="green", width=12)

    for entry in scoreboard:
        rank_emoji = get_rank_emoji(entry.pos)
        rank_style = get_rank_style(entry.pos)

        # Highlight current user/team
        name_style = "cyan"
        is_current_account = False

        # Check if this is the current user
        if current_user and entry.account_name == current_user.name:
            is_current_account = True

        # Check if this is the current team
        if current_team and entry.account_name == current_team.get('name'):
            is_current_account = True

        if is_current_account:
            name_style = "bold yellow"
            rank_emoji = "👤"

        table.add_row(
            f"[{rank_style}]{rank_emoji} #{entry.pos}[/{rank_style}]",
            f"[{name_style}]{entry.account_name}[/{name_style}]",
            f"[bold green]{entry.score:,}[/bold green]"
        )

    console.print(table)

    # Show current user/team info if available
    if current_team:
        team_info = f"Your team: {current_team['name']} | Position: #{current_team.get('place', 'Unknown')} | Score: {current_team.get('score', 0):,}"
        team_panel = Panel(
            team_info,
            title="👤 Your Team Stats",
            border_style="yellow"
        )
        console.print(team_panel)
    elif current_user:
        user_info = f"Your position: #{current_user.place} | Score: {current_user.score:,}"
        user_panel = Panel(
            user_info,
            title="👤 Your Stats",
            border_style="yellow"
        )
        console.print(user_panel)


def _display_detailed_scoreboard(scoreboard, ctf_info, current_user, current_team, limit=None):
    """Display detailed scoreboard with enhanced table format."""

    # Apply limit if specified
    display_scoreboard = scoreboard
    if limit and limit > 0:
        display_scoreboard = scoreboard[:limit]

    # Create a detailed table
    table = Table(
        title=f"🏆 {ctf_info.name} - Detailed Scoreboard",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Rank", style="yellow", width=8)
    table.add_column("Team/User", style="cyan", min_width=20)
    table.add_column("Score", style="green", width=12)
    table.add_column("Status", style="white", width=10)

    for entry in display_scoreboard:
        rank_emoji = get_rank_emoji(entry.pos)
        rank_style = get_rank_style(entry.pos)

        # Highlight current user/team
        name_style = "cyan"
        status = ""
        is_current_account = False

        # Check if this is the current user
        if current_user and entry.account_name == current_user.name:
            is_current_account = True

        # Check if this is the current team
        if current_team and entry.account_name == current_team.get('name'):
            is_current_account = True

        if is_current_account:
            name_style = "bold yellow"
            status = "👤 YOU"

        # Add medal/trophy indicators for top positions
        if entry.pos <= 3:
            status = "🏆 PODIUM"
        elif entry.pos <= 10:
            status = "🌟 TOP 10"

        table.add_row(
            f"[{rank_style}]{rank_emoji} #{entry.pos}[/{rank_style}]",
            f"[{name_style}]{entry.account_name}[/{name_style}]",
            f"[bold green]{entry.score:,}[/bold green]",
            status
        )

    console.print(table)

    # Stats summary
    if scoreboard:
        _display_scoreboard_stats(scoreboard, current_user)




def _display_scoreboard_stats(scoreboard, current_user):
    """Display scoreboard statistics."""
    if not scoreboard:
        return

    total_participants = len(scoreboard)
    top_score = scoreboard[0].score
    avg_score = sum(entry.score for entry in scoreboard) / total_participants

    stats = [
        f"📊 Total Participants: {total_participants}",
        f"🏆 Top Score: {top_score:,}",
        f"📈 Average Score: {avg_score:,.0f}"
    ]

    if current_user:
        percentile = ((total_participants - current_user.place + 1) / total_participants) * 100
        stats.append(f"👤 Your Percentile: {percentile:.1f}%")

    stats_panel = Panel(
        "\n".join(stats),
        title="📈 Statistics",
        border_style="blue"
    )
    console.print(stats_panel)


@app.command("top")
def top_players(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    count: int = typer.Option(10, "--count", "-c", help="Number of top players to show")
):
    """Show top players only."""
    show_scoreboard(profile=profile, count=count, detailed=True)


@app.command("me")
def my_position(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Show your position and nearby players."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        current_user = client.get_me()
        if not current_user:
            console.print("[red]❌ Could not get user information[/red]")
            raise typer.Exit(1)

        # Get large scoreboard to find nearby players
        scoreboard = client.get_scoreboard(200)
        my_entry = next((entry for entry in scoreboard if entry.account_name == current_user.name), None)

        if not my_entry:
            console.print("[yellow]Could not find your position in scoreboard[/yellow]")
            return

        # Show user info
        user_info = [
            f"Name: {current_user.name}",
            f"Rank: #{current_user.place}",
            f"Score: {current_user.score:,}",
            f"Affiliation: {current_user.affiliation or 'None'}"
        ]

        user_panel = Panel(
            "\n".join(user_info),
            title="👤 Your Profile",
            border_style="yellow"
        )
        console.print(user_panel)

        # Show nearby players (±5 positions)
        my_idx = scoreboard.index(my_entry)
        start_idx = max(0, my_idx - 5)
        end_idx = min(len(scoreboard), my_idx + 6)
        nearby = scoreboard[start_idx:end_idx]

        table = Table(title="🔍 Nearby Players", show_header=True, header_style="bold magenta")
        table.add_column("Rank", style="yellow", width=8)
        table.add_column("Name", style="cyan", min_width=20)
        table.add_column("Score", style="green", width=12)
        table.add_column("Diff", style="red", width=10)

        for entry in nearby:
            rank_emoji = get_rank_emoji(entry.pos)
            name_style = "bold yellow" if entry.account_name == current_user.name else "cyan"

            # Calculate score difference
            score_diff = entry.score - current_user.score
            diff_text = ""
            if score_diff > 0:
                diff_text = f"+{score_diff:,}"
            elif score_diff < 0:
                diff_text = f"{score_diff:,}"

            table.add_row(
                f"{rank_emoji} #{entry.pos}",
                f"[{name_style}]{entry.account_name}[/{name_style}]",
                f"{entry.score:,}",
                diff_text
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Failed to get position: {e}[/red]")
        raise typer.Exit(1)


@app.command("stats")
def scoreboard_stats(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Show detailed scoreboard statistics."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        ctf_info = client.get_ctf_info()
        scoreboard = client.get_scoreboard(200)  # Get more entries for better stats

        if not scoreboard:
            console.print("[yellow]No scoreboard data available[/yellow]")
            return

        # Calculate statistics
        scores = [entry.score for entry in scoreboard]
        total_participants = len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_score = sum(scores) / total_participants
        median_score = sorted(scores)[total_participants // 2]

        # Score distribution
        ranges = [
            (0, 100, "0-100"),
            (101, 500, "101-500"),
            (501, 1000, "501-1K"),
            (1001, 5000, "1K-5K"),
            (5001, float('inf'), "5K+")
        ]

        distribution = {}
        for low, high, label in ranges:
            count = len([s for s in scores if low <= s <= high])
            distribution[label] = count

        # Display stats
        stats_table = Table(title=f"📈 {ctf_info.name} - Statistics", show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Total Participants", f"{total_participants:,}")
        stats_table.add_row("Highest Score", f"{max_score:,}")
        stats_table.add_row("Lowest Score", f"{min_score:,}")
        stats_table.add_row("Average Score", f"{avg_score:,.0f}")
        stats_table.add_row("Median Score", f"{median_score:,}")

        console.print(stats_table)

        # Score distribution
        dist_table = Table(title="📊 Score Distribution", show_header=True, header_style="bold blue")
        dist_table.add_column("Score Range", style="cyan")
        dist_table.add_column("Participants", style="green")
        dist_table.add_column("Percentage", style="yellow")

        for label, count in distribution.items():
            percentage = (count / total_participants) * 100
            dist_table.add_row(label, str(count), f"{percentage:.1f}%")

        console.print(dist_table)

    except Exception as e:
        console.print(f"[red]❌ Failed to get statistics: {e}[/red]")
        raise typer.Exit(1)