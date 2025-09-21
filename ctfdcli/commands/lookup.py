"""Lookup commands for remote teams and users."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from typing import Optional

from ..core import ConfigManager, CTFdClient
from ..utils import show_subcommands

app = typer.Typer(help="Lookup information about remote teams and users")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Lookup information about remote teams and users."""
    if ctx.invoked_subcommand is None:
        # Show available subcommands
        subcommands = [
            ("team", "👥 Lookup team information by ID or name"),
            ("user", "👤 Lookup user information by ID or name"),
        ]

        show_subcommands(
            "lookup",
            subcommands,
            "Search and view information about remote teams and users"
        )


@app.command("team")
def lookup_team(
    team_identifier: str = typer.Argument(..., help="Team ID or team name to lookup"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information including solves")
):
    """Lookup information about a remote team by ID or name."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Looking up team '{team_identifier}'...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        team_data = None

        # Try to lookup by ID first (if it's a number)
        if team_identifier.isdigit():
            team_id = int(team_identifier)
            team_data = client.get_team_info(team_id)

        # If not found or not a number, search by name
        if not team_data:
            teams = client.search_teams(team_identifier)
            if teams:
                if len(teams) == 1:
                    team_data = teams[0]
                else:
                    _display_team_search_results(teams)
                    return
            else:
                console.print(f"[red]❌ No team found matching '{team_identifier}'[/red]")
                raise typer.Exit(1)

        if not team_data:
            console.print(f"[red]❌ Team '{team_identifier}' not found[/red]")
            raise typer.Exit(1)

        # Display team information
        _display_team_info(team_data, client, detailed)

    except Exception as e:
        console.print(f"[red]❌ Failed to lookup team: {e}[/red]")
        raise typer.Exit(1)


@app.command("user")
def lookup_user(
    user_identifier: str = typer.Argument(..., help="User ID or username to lookup"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information including solves")
):
    """Lookup information about a remote user by ID or name."""

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Looking up user '{user_identifier}'...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        user_data = None

        # Try to lookup by ID first (if it's a number)
        if user_identifier.isdigit():
            user_id = int(user_identifier)
            user_data = client.get_user_info(user_id)

        # If not found or not a number, search by name
        if not user_data:
            users = client.search_users(user_identifier)
            if users:
                if len(users) == 1:
                    user_data = users[0]
                else:
                    _display_user_search_results(users)
                    return
            else:
                console.print(f"[red]❌ No user found matching '{user_identifier}'[/red]")
                raise typer.Exit(1)

        if not user_data:
            console.print(f"[red]❌ User '{user_identifier}' not found[/red]")
            raise typer.Exit(1)

        # Display user information
        _display_user_info(user_data, client, detailed)

    except Exception as e:
        console.print(f"[red]❌ Failed to lookup user: {e}[/red]")
        raise typer.Exit(1)


def _display_team_search_results(teams):
    """Display multiple team search results for user to choose from."""
    console.print(f"[yellow]Found {len(teams)} teams matching your search:[/yellow]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Team Name", style="cyan", min_width=25)
    table.add_column("Score", style="green", width=10)
    table.add_column("Place", style="yellow", width=8)

    for team in teams:
        table.add_row(
            str(team.get('id', 'N/A')),
            team.get('name', 'Unknown'),
            str(team.get('score', 0)),
            str(team.get('place', 'N/A'))
        )

    console.print(table)
    console.print("\n[cyan]💡 Tip: Use the exact team ID or name for a specific lookup[/cyan]")


def _display_user_search_results(users):
    """Display multiple user search results for user to choose from."""
    console.print(f"[yellow]Found {len(users)} users matching your search:[/yellow]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Username", style="cyan", min_width=20)
    table.add_column("Score", style="green", width=10)
    table.add_column("Place", style="yellow", width=8)
    table.add_column("Affiliation", style="blue", width=20)

    for user in users:
        table.add_row(
            str(user.get('id', 'N/A')),
            user.get('name', 'Unknown'),
            str(user.get('score', 0)),
            str(user.get('place', 'N/A')),
            user.get('affiliation', '-') or '-'
        )

    console.print(table)
    console.print("\n[cyan]💡 Tip: Use the exact user ID or name for a specific lookup[/cyan]")


def _display_team_info(team_data, client, detailed=False):
    """Display comprehensive team information."""

    # Basic team info
    team_id = team_data.get('id', 'Unknown')
    team_name = team_data.get('name', 'Unknown')
    team_score = team_data.get('score', 0)
    team_place = team_data.get('place', 'Unknown')

    # Create main info panel
    main_info = []
    main_info.append(f"[cyan]Team ID:[/cyan] {team_id}")
    main_info.append(f"[cyan]Team Name:[/cyan] {team_name}")
    main_info.append(f"[cyan]Score:[/cyan] {team_score:,}")
    main_info.append(f"[cyan]Position:[/cyan] #{team_place}")

    if team_data.get('affiliation'):
        main_info.append(f"[cyan]Affiliation:[/cyan] {team_data['affiliation']}")

    if team_data.get('website'):
        main_info.append(f"[cyan]Website:[/cyan] {team_data['website']}")

    if team_data.get('country'):
        main_info.append(f"[cyan]Country:[/cyan] {team_data['country']}")

    info_panel = Panel(
        "\n".join(main_info),
        title=f"👥 Team Information",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(info_panel)

    # Team members if available
    members = team_data.get('members', [])
    if members:
        console.print(f"\n[bold cyan]👥 Team Members ({len(members)}):[/bold cyan]")

        members_table = Table(show_header=True, header_style="bold magenta")
        members_table.add_column("ID", style="dim", width=8)
        members_table.add_column("Name", style="cyan", min_width=15)
        members_table.add_column("Score", style="green", width=10)
        members_table.add_column("Role", style="yellow", width=10)

        captain_id = team_data.get('captain_id')
        for member_id in members:
            try:
                member_data = client.get_user_info(member_id)
                if member_data:
                    member_name = member_data.get('name', f'User {member_id}')
                    member_score = member_data.get('score', 0)
                    role = "Captain" if member_id == captain_id else "Member"

                    members_table.add_row(
                        str(member_id),
                        member_name,
                        f"{member_score:,}",
                        role
                    )
                else:
                    role = "Captain" if member_id == captain_id else "Member"
                    members_table.add_row(
                        str(member_id),
                        f"User {member_id}",
                        "Unknown",
                        role
                    )
            except Exception:
                role = "Captain" if member_id == captain_id else "Member"
                members_table.add_row(
                    str(member_id),
                    f"User {member_id}",
                    "Unknown",
                    role
                )

        console.print(members_table)

    # Show team solve information (always display)
    console.print(f"\n[bold green]🏆 Team Solves:[/bold green]")
    try:
        solves = client.get_team_solves(int(team_id))
        if solves:
            # Get challenge information to show names
            challenges = client.get_challenges()
            challenge_map = {c.id: c for c in challenges}

            solves_table = Table(show_header=True, header_style="bold magenta")
            solves_table.add_column("Challenge", style="cyan", min_width=20)
            solves_table.add_column("Category", style="blue", width=15)
            solves_table.add_column("Points", style="green", width=8)
            solves_table.add_column("Solved At", style="yellow", width=20)

            total_points = 0
            for solve in solves:
                challenge_id = solve.get('challenge_id')
                challenge = challenge_map.get(challenge_id)
                if challenge:
                    challenge_name = challenge.name
                    category = challenge.category
                    points = challenge.value
                    total_points += points
                else:
                    challenge_name = f"Challenge {challenge_id}"
                    category = "Unknown"
                    points = solve.get('value', 0)

                # Format solve time
                solve_time = solve.get('date', 'Unknown')
                if solve_time != 'Unknown':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(solve_time.replace('Z', '+00:00'))
                        solve_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass

                solves_table.add_row(
                    challenge_name,
                    category,
                    str(points),
                    solve_time
                )

            console.print(solves_table)
            console.print(f"\n[green]Total points from solves: {total_points:,}[/green]")
        else:
            console.print("[yellow]No solves found for this team[/yellow]")

    except Exception as e:
        console.print(f"[yellow]Could not fetch team solves: {e}[/yellow]")

    # Additional detailed information (only in detailed mode)
    if detailed:
        # Could add more detailed statistics here in the future
        pass


def _display_user_info(user_data, client, detailed=False):
    """Display comprehensive user information."""

    # Basic user info
    user_id = user_data.get('id', 'Unknown')
    username = user_data.get('name', 'Unknown')
    user_score = user_data.get('score', 0)
    user_place = user_data.get('place', 'Unknown')

    # Create main info panel
    main_info = []
    main_info.append(f"[cyan]User ID:[/cyan] {user_id}")
    main_info.append(f"[cyan]Username:[/cyan] {username}")
    main_info.append(f"[cyan]Score:[/cyan] {user_score:,}")
    main_info.append(f"[cyan]Position:[/cyan] #{user_place}")

    if user_data.get('affiliation'):
        main_info.append(f"[cyan]Affiliation:[/cyan] {user_data['affiliation']}")

    if user_data.get('website'):
        main_info.append(f"[cyan]Website:[/cyan] {user_data['website']}")

    if user_data.get('country'):
        main_info.append(f"[cyan]Country:[/cyan] {user_data['country']}")

    if user_data.get('email'):
        main_info.append(f"[cyan]Email:[/cyan] {user_data['email']}")

    info_panel = Panel(
        "\n".join(main_info),
        title=f"👤 User Information",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(info_panel)

    # Show solve information (always display)
    console.print(f"\n[bold green]🏆 User Solves:[/bold green]")
    try:
        solves = client.get_user_solves(int(user_id))
        if solves:
            # Get challenge information to show names
            challenges = client.get_challenges()
            challenge_map = {c.id: c for c in challenges}

            solves_table = Table(show_header=True, header_style="bold magenta")
            solves_table.add_column("Challenge", style="cyan", min_width=20)
            solves_table.add_column("Category", style="blue", width=15)
            solves_table.add_column("Points", style="green", width=8)
            solves_table.add_column("Solved At", style="yellow", width=20)

            total_points = 0
            for solve in solves:
                challenge_id = solve.get('challenge_id')
                challenge = challenge_map.get(challenge_id)
                if challenge:
                    challenge_name = challenge.name
                    category = challenge.category
                    points = challenge.value
                    total_points += points
                else:
                    challenge_name = f"Challenge {challenge_id}"
                    category = "Unknown"
                    points = solve.get('value', 0)

                # Format solve time
                solve_time = solve.get('date', 'Unknown')
                if solve_time != 'Unknown':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(solve_time.replace('Z', '+00:00'))
                        solve_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass

                solves_table.add_row(
                    challenge_name,
                    category,
                    str(points),
                    solve_time
                )

            console.print(solves_table)
            console.print(f"\n[green]Total points from solves: {total_points:,}[/green]")
        else:
            console.print("[yellow]No solves found for this user[/yellow]")

    except Exception as e:
        console.print(f"[yellow]Could not fetch user solves: {e}[/yellow]")

    # Additional detailed information (only in detailed mode)
    if detailed:
        # Could add more detailed statistics here in the future
        pass