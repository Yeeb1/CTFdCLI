"""Challenge listing and management commands."""

import typer
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from typing import Optional, List, Dict, Tuple

from ..core import ConfigManager, CTFdClient
from ..utils import show_subcommands

app = typer.Typer(help="List and manage challenges")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """List and manage challenges."""
    if ctx.invoked_subcommand is None:
        # Show available subcommands
        subcommands = [
            ("list", "📋 List all available challenges with filters"),
            ("show", "🔍 Show detailed information about a specific challenge"),
            ("solved", "✅ List only solved challenges"),
            ("unsolved", "❌ List only unsolved challenges"),
            ("categories", "📂 List all available categories with statistics"),
            ("connection", "🔌 Extract connection details from challenge descriptions"),
        ]

        show_subcommands(
            "challenges",
            subcommands,
            "Manage and view CTF challenges"
        )


def get_difficulty_style(points: int) -> str:
    """Get color style based on challenge points.

    Args:
        points: Challenge points

    Returns:
        Rich style string
    """
    if points <= 100:
        return "green"
    elif points <= 300:
        return "yellow"
    elif points <= 500:
        return "orange"
    else:
        return "red"


def format_challenge_status(solved: bool) -> str:
    """Format challenge status with emoji.

    Args:
        solved: Whether challenge is solved

    Returns:
        Formatted status string
    """
    return "✅" if solved else "❌"


def format_challenge_type(challenge_type: str, short: bool = False) -> str:
    """Format challenge type with appropriate indicator.

    Args:
        challenge_type: Challenge type
        short: Whether to use short format for tables

    Returns:
        Formatted type string
    """
    if short:
        type_short = {
            "standard": "STD",
            "multiple_choice": "MC",
            "dynamic": "DYN",
            "static": "STC",
            "regex": "RGX",
            "code": "CODE",
            "upload": "UPL",
            "king_of_the_hill": "KOTH"
        }
        return type_short.get(challenge_type, challenge_type.upper()[:4])
    else:
        type_full = {
            "standard": "📝 Standard",
            "multiple_choice": "☑️ Multiple Choice",
            "dynamic": "⚡ Dynamic",
            "static": "🔒 Static",
            "regex": "🔄 Regex",
            "code": "💻 Code",
            "upload": "📤 Upload",
            "king_of_the_hill": "👑 King of the Hill"
        }
        return type_full.get(challenge_type, f"❓ {challenge_type.title()}")


def format_attempts_info(attempts: int, max_attempts: Optional[int]) -> str:
    """Format attempts information.

    Args:
        attempts: Current number of attempts
        max_attempts: Maximum allowed attempts (None if unlimited)

    Returns:
        Formatted attempts string
    """
    if max_attempts is None:
        return f"{attempts}/∞"
    else:
        style = "red" if attempts >= max_attempts else "yellow" if attempts >= max_attempts * 0.8 else "green"
        return f"[{style}]{attempts}/{max_attempts}[/{style}]"


def parse_connection_info(connection_info: str) -> Dict[str, str]:
    """Parse connection details from CTFd connection_info field.

    Args:
        connection_info: Connection info string from CTFd API

    Returns:
        Dictionary with connection details including type, host, port, command, icon
    """
    if not connection_info:
        return None

    # Check for HTTP/HTTPS URLs
    if connection_info.startswith(('http://', 'https://')):
        import urllib.parse
        parsed = urllib.parse.urlparse(connection_info)
        port = str(parsed.port) if parsed.port else ('443' if parsed.scheme == 'https' else '80')

        return {
            'type': 'web',
            'host': parsed.hostname or parsed.netloc,
            'port': port,
            'command': connection_info,
            'icon': '🌐',
            'full_url': connection_info
        }

    # Check for netcat pattern: nc host port
    nc_match = re.match(r'nc\s+([a-zA-Z0-9.-]+)\s+(\d+)', connection_info)
    if nc_match:
        host, port = nc_match.groups()
        return {
            'type': 'netcat',
            'host': host,
            'port': port,
            'command': connection_info,
            'icon': '🔌'
        }

    # Check for SSH pattern
    if connection_info.startswith('ssh '):
        ssh_part = connection_info[4:]  # Remove 'ssh ' prefix
        host = ssh_part.split('@')[-1] if '@' in ssh_part else ssh_part
        return {
            'type': 'ssh',
            'host': host,
            'port': '22',
            'command': connection_info,
            'icon': '🔐'
        }

    # Check for telnet pattern
    if connection_info.startswith('telnet '):
        telnet_parts = connection_info.split()
        if len(telnet_parts) >= 3:
            host, port = telnet_parts[1], telnet_parts[2]
        else:
            host, port = telnet_parts[1] if len(telnet_parts) > 1 else '', '23'

        return {
            'type': 'telnet',
            'host': host,
            'port': port,
            'command': connection_info,
            'icon': '📞'
        }

    # Check for host:port pattern
    hostport_match = re.match(r'([a-zA-Z0-9.-]+):(\d+)', connection_info)
    if hostport_match:
        host, port = hostport_match.groups()
        return {
            'type': 'generic',
            'host': host,
            'port': port,
            'command': f'nc {host} {port}',
            'icon': '🔗',
            'original': connection_info
        }

    # If no pattern matches, treat as generic connection info
    return {
        'type': 'other',
        'host': 'N/A',
        'port': 'N/A',
        'command': connection_info,
        'icon': '❓',
        'original': connection_info
    }


@app.command("list")
def list_challenges(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    solved: Optional[bool] = typer.Option(None, "--solved/--unsolved", help="Filter by solved status"),
    sort_by: str = typer.Option("category", "--sort", help="Sort by: category, name, points, solves"),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse sort order"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information")
):
    """List all available challenges."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Fetching challenges from {profile_obj.url}...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get challenges (solve status is already included)
        challenges = client.get_challenges()

        if not challenges:
            console.print("[yellow]No challenges found[/yellow]")
            return

        # Get CTF info for title
        try:
            ctf_info = client.get_ctf_info()
            ctf_name = ctf_info.name
        except Exception:
            ctf_name = "CTF"

        # Get team member solve information if in team mode
        challenge_solvers = {}
        team_members = {}
        try:
            challenge_solvers = client.get_challenge_solvers()
            # Get team member names
            team_data = client._make_request('GET', '/teams/me')
            for member_id in team_data.get('members', []):
                try:
                    member_data = client._make_request('GET', f'/users/{member_id}')
                    team_members[member_id] = member_data.get('name', f'User {member_id}')
                except Exception:
                    team_members[member_id] = f'User {member_id}'
        except Exception:
            pass  # Not in team mode or API error

        # Apply filters
        filtered_challenges = challenges

        if category:
            filtered_challenges = [c for c in filtered_challenges if c.category.lower() == category.lower()]

        if solved is not None:
            filtered_challenges = [c for c in filtered_challenges if c.solved_by_me == solved]

        if not filtered_challenges:
            console.print("[yellow]No challenges match the specified filters[/yellow]")
            return

        # Sort challenges
        sort_key_map = {
            "category": lambda c: c.category,
            "name": lambda c: c.name,
            "points": lambda c: c.value,
            "solves": lambda c: c.solves
        }

        if sort_by in sort_key_map:
            filtered_challenges.sort(key=sort_key_map[sort_by], reverse=reverse)

        # Display results
        if detailed:
            _display_detailed_challenges(filtered_challenges, ctf_name, challenge_solvers, team_members)
        else:
            _display_challenges_table(filtered_challenges, ctf_name, challenge_solvers, team_members)

        # Show summary
        total_challenges = len(challenges)
        solved_count = len([c for c in challenges if c.solved_by_me])
        displayed_count = len(filtered_challenges)

        summary_text = f"Showing {displayed_count} of {total_challenges} challenges"
        if solved_count > 0:
            summary_text += f" | {solved_count} solved ({solved_count/total_challenges*100:.1f}%)"

        console.print(f"\n[cyan]{summary_text}[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch challenges: {e}[/red]")
        raise typer.Exit(1)


def _display_challenges_table(challenges, ctf_name="CTF", challenge_solvers=None, team_members=None):
    """Display challenges in a table format."""
    challenge_solvers = challenge_solvers or {}
    team_members = team_members or {}

    table = Table(title=f"🚩 {ctf_name} - Challenges", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Status", width=6)
    table.add_column("Name", style="cyan", min_width=15)
    table.add_column("Category", style="blue", width=12)
    table.add_column("Type", style="magenta", width=10)
    table.add_column("Points", style="green", width=8)
    table.add_column("Solves", style="yellow", width=6)
    table.add_column("Attempts", style="red", width=10)

    # Add "Solved By" column if we have team information
    if team_members:
        table.add_column("Solved By", style="green", width=15)

    for challenge in challenges:
        status = format_challenge_status(challenge.solved_by_me)
        points_style = get_difficulty_style(challenge.value)

        # Prepare row data
        row_data = [
            str(challenge.id),
            status,
            challenge.name,
            challenge.category,
            format_challenge_type(challenge.type, short=True),
            f"[{points_style}]{challenge.value}[/{points_style}]",
            str(challenge.solves),
            format_attempts_info(challenge.attempts, challenge.max_attempts)
        ]

        # Add solver information if available
        if team_members:
            solvers = challenge_solvers.get(challenge.id, [])
            if solvers:
                solver_names = [team_members.get(solver_id, f"User {solver_id}") for solver_id in solvers]
                row_data.append(", ".join(solver_names))
            else:
                row_data.append("-")

        table.add_row(*row_data)

    console.print(table)


def _display_detailed_challenges(challenges, ctf_name="CTF", challenge_solvers=None, team_members=None):
    """Display challenges in detailed card format."""
    challenge_solvers = challenge_solvers or {}
    team_members = team_members or {}
    cards = []

    for challenge in challenges:
        status = format_challenge_status(challenge.solved_by_me)
        points_style = get_difficulty_style(challenge.value)

        # Create challenge card
        content = []
        content.append(f"[bold cyan]{challenge.name}[/bold cyan]")
        content.append(f"Category: [blue]{challenge.category}[/blue]")
        content.append(f"Type: [magenta]{format_challenge_type(challenge.type)}[/magenta]")
        content.append(f"Points: [{points_style}]{challenge.value}[/{points_style}]")
        content.append(f"Solves: [yellow]{challenge.solves}[/yellow]")
        content.append(f"Attempts: {format_attempts_info(challenge.attempts, challenge.max_attempts)}")
        content.append(f"Status: {status}")

        if challenge.tags:
            content.append(f"Tags: {', '.join(challenge.tags)}")

        # Add solver information if available
        if team_members:
            solvers = challenge_solvers.get(challenge.id, [])
            if solvers:
                solver_names = [team_members.get(solver_id, f"User {solver_id}") for solver_id in solvers]
                content.append(f"Solved by: [green]{', '.join(solver_names)}[/green]")

        # Truncate description
        desc = challenge.description
        if len(desc) > 100:
            desc = desc[:100] + "..."
        content.append(f"\n{desc}")

        card = Panel(
            "\n".join(content),
            title=f"ID: {challenge.id}",
            border_style="green" if challenge.solved_by_me else "white"
        )
        cards.append(card)

    # Display in columns
    console.print(Columns(cards, equal=True, expand=True))


@app.command("show")
def show_challenge(
    challenge_id: int = typer.Argument(..., help="Challenge ID"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Show detailed information about a specific challenge."""

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

        # Get all challenges to find the specific one
        challenges = client.get_challenges()
        challenge = next((c for c in challenges if c.id == challenge_id), None)

        if not challenge:
            console.print(f"[red]Challenge with ID {challenge_id} not found[/red]")
            raise typer.Exit(1)

        # Solve status is already included in challenge data

        # Display detailed information
        status = "✅ Solved" if challenge.solved_by_me else "❌ Not solved"
        points_style = get_difficulty_style(challenge.value)

        details = []
        details.append(f"[bold cyan]Name:[/bold cyan] {challenge.name}")
        details.append(f"[bold cyan]ID:[/bold cyan] {challenge.id}")
        details.append(f"[bold cyan]Category:[/bold cyan] {challenge.category}")
        details.append(f"[bold cyan]Type:[/bold cyan] {format_challenge_type(challenge.type)}")
        details.append(f"[bold cyan]Points:[/bold cyan] [{points_style}]{challenge.value}[/{points_style}]")
        details.append(f"[bold cyan]Solves:[/bold cyan] {challenge.solves}")
        details.append(f"[bold cyan]Attempts:[/bold cyan] {format_attempts_info(challenge.attempts, challenge.max_attempts)}")
        details.append(f"[bold cyan]Status:[/bold cyan] {status}")

        if challenge.tags:
            details.append(f"[bold cyan]Tags:[/bold cyan] {', '.join(challenge.tags)}")

        if challenge.max_attempts:
            details.append(f"[bold cyan]Max Attempts:[/bold cyan] {challenge.max_attempts}")

        # Add connection information if available
        if challenge.connection_info:
            connection = parse_connection_info(challenge.connection_info)
            if connection:
                details.append(f"\n[bold cyan]Connection:[/bold cyan]")
                details.append(f"  {connection['icon']} Type: {connection['type'].title()}")
                details.append(f"  🏠 Host: {connection['host']}")
                details.append(f"  🔌 Port: {connection['port']}")
                details.append(f"  💻 Command: [cyan]{connection['command']}[/cyan]")

        details.append(f"\n[bold cyan]Description:[/bold cyan]\n{challenge.description}")

        if challenge.files:
            details.append(f"\n[bold cyan]Files:[/bold cyan]")
            for file in challenge.files:
                details.append(f"  • {file}")

        if challenge.hints:
            details.append(f"\n[bold cyan]Hints:[/bold cyan]")
            for i, hint in enumerate(challenge.hints, 1):
                details.append(f"  {i}. {hint.get('content', 'No content')}")

        panel = Panel(
            "\n".join(details),
            title=f"🚩 Challenge Details",
            border_style="green" if challenge.solved_by_me else "cyan",
            padding=(1, 2)
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch challenge: {e}[/red]")
        raise typer.Exit(1)


@app.command("solved")
def list_solved(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    sort_by: str = typer.Option("category", "--sort", help="Sort by: category, name, points, solves"),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse sort order"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information")
):
    """List only solved challenges."""
    list_challenges(
        profile=profile,
        category=category,
        solved=True,
        sort_by=sort_by,
        reverse=reverse,
        detailed=detailed
    )


@app.command("unsolved")
def list_unsolved(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    sort_by: str = typer.Option("category", "--sort", help="Sort by: category, name, points, solves"),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse sort order"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information")
):
    """List only unsolved challenges."""
    list_challenges(
        profile=profile,
        category=category,
        solved=False,
        sort_by=sort_by,
        reverse=reverse,
        detailed=detailed
    )


@app.command("categories")
def list_categories(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """List all available categories."""

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

        challenges = client.get_challenges()

        if not challenges:
            console.print("[yellow]No challenges found[/yellow]")
            return

        # Group by category
        categories = {}
        for challenge in challenges:
            category = challenge.category
            if category not in categories:
                categories[category] = {"total": 0, "solved": 0, "points": 0}

            categories[category]["total"] += 1
            categories[category]["points"] += challenge.value

            if challenge.solved_by_me:
                categories[category]["solved"] += 1

        # Display categories table
        table = Table(title="📂 Challenge Categories", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Challenges", style="blue", width=15)
        table.add_column("Solved", style="green", width=10)
        table.add_column("Progress", style="yellow", width=15)
        table.add_column("Total Points", style="red", width=15)

        for category, stats in sorted(categories.items()):
            solved = stats["solved"]
            total = stats["total"]
            progress = f"{solved}/{total} ({solved/total*100:.1f}%)"

            table.add_row(
                category,
                str(total),
                str(solved),
                progress,
                str(stats["points"])
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch categories: {e}[/red]")
        raise typer.Exit(1)


@app.command("connection")
def list_connections(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    challenge_id: Optional[int] = typer.Option(None, "--id", help="Show connections for specific challenge ID"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    solved: Optional[bool] = typer.Option(None, "--solved/--unsolved", help="Filter by solved status"),
    copy: bool = typer.Option(False, "--copy", help="Copy first connection command to clipboard (requires xclip/pbcopy)")
):
    """Extract and display connection details from challenge descriptions."""

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

        challenges = client.get_challenges()

        if not challenges:
            console.print("[yellow]No challenges found[/yellow]")
            return

        # Filter challenges
        filtered_challenges = challenges

        if challenge_id is not None:
            filtered_challenges = [c for c in filtered_challenges if c.id == challenge_id]
            if not filtered_challenges:
                console.print(f"[red]Challenge with ID {challenge_id} not found[/red]")
                raise typer.Exit(1)

        if category:
            filtered_challenges = [c for c in filtered_challenges if c.category.lower() == category.lower()]

        if solved is not None:
            filtered_challenges = [c for c in filtered_challenges if c.solved_by_me == solved]

        # Extract connections from all filtered challenges
        challenge_connections = {}
        all_connections = []

        for challenge in filtered_challenges:
            if challenge.connection_info:
                connection = parse_connection_info(challenge.connection_info)
                if connection:
                    challenge_connections[challenge.id] = {
                        'challenge': challenge,
                        'connection': connection
                    }
                    all_connections.append(connection)

        if not all_connections:
            console.print("[yellow]No connection details found in challenges[/yellow]")
            return

        # Get CTF info for title
        try:
            ctf_info = client.get_ctf_info()
            ctf_name = ctf_info.name
        except Exception:
            ctf_name = "CTF"

        # Display connections in a more readable format
        console.print(f"\n[bold magenta]🔌 {ctf_name} - Connection Details[/bold magenta]\n")

        first_command = None
        for challenge_id, data in challenge_connections.items():
            challenge = data['challenge']
            connection = data['connection']

            status_emoji = "✅" if challenge.solved_by_me else "❌"

            # Create a panel for each connection
            connection_info = []
            connection_info.append(f"[bold cyan]Challenge:[/bold cyan] {challenge.name} {status_emoji}")
            connection_info.append(f"[bold blue]Type:[/bold blue] {connection['icon']} {connection['type'].title()}")
            connection_info.append(f"[bold green]Host:[/bold green] {connection['host']}")
            connection_info.append(f"[bold yellow]Port:[/bold yellow] {connection['port']}")
            connection_info.append(f"[bold white]Command:[/bold white] [cyan]{connection['command']}[/cyan]")

            panel = Panel(
                "\n".join(connection_info),
                border_style="green" if challenge.solved_by_me else "cyan",
                padding=(0, 1)
            )
            console.print(panel)

            # Store first command for copying
            if first_command is None:
                first_command = connection['command']

        # Show summary
        total_connections = len(all_connections)
        unique_hosts = len(set(conn['host'] for conn in all_connections))
        connection_types = set(conn['type'] for conn in all_connections)

        summary_text = f"Found {total_connections} connections across {unique_hosts} unique hosts"
        summary_text += f" | Types: {', '.join(sorted(connection_types))}"

        console.print(f"\n[cyan]{summary_text}[/cyan]")

        # Copy to clipboard if requested
        if copy and first_command:
            try:
                import subprocess
                import shutil

                # Try different clipboard commands
                if shutil.which('xclip'):
                    subprocess.run(['xclip', '-selection', 'clipboard'], input=first_command.encode(), check=True)
                    console.print(f"[green]✅ Copied to clipboard: {first_command}[/green]")
                elif shutil.which('pbcopy'):
                    subprocess.run(['pbcopy'], input=first_command.encode(), check=True)
                    console.print(f"[green]✅ Copied to clipboard: {first_command}[/green]")
                elif shutil.which('wl-copy'):
                    subprocess.run(['wl-copy'], input=first_command.encode(), check=True)
                    console.print(f"[green]✅ Copied to clipboard: {first_command}[/green]")
                else:
                    console.print("[yellow]⚠️ No clipboard utility found (xclip, pbcopy, or wl-copy)[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Failed to copy to clipboard: {e}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch challenges: {e}[/red]")
        raise typer.Exit(1)