"""Team information commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Optional

from ..core import ConfigManager, CTFdClient

app = typer.Typer(help="View team information")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Show detailed information about your team."""

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
    console.print(f"[cyan]Fetching team information from {profile_obj.url}...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get team information
        try:
            team_data = client._make_request('GET', '/teams/me')
            if not team_data:
                console.print("[yellow]No team information available. This might be a user-mode CTF.[/yellow]")
                return
        except Exception as e:
            console.print(f"[red]❌ Failed to get team information: {e}[/red]")
            console.print("[yellow]This might be a user-mode CTF or you might not be on a team.[/yellow]")
            return

        # Display team information
        _display_team_info(team_data, client)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch team information: {e}[/red]")
        raise typer.Exit(1)


def _display_team_info(team_data, client):
    """Display comprehensive team information."""

    # Basic team info
    team_name = team_data.get('name', 'Unknown')
    team_score = team_data.get('score', 0)
    team_place = team_data.get('place', 'Unknown')
    team_id = team_data.get('id', 'Unknown')

    # Create main info panel
    main_info = []
    main_info.append(f"[cyan]Team Name:[/cyan] {team_name}")
    main_info.append(f"[cyan]Team ID:[/cyan] {team_id}")
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

    # Team members
    members = team_data.get('members', [])
    if members:
        console.print(f"\n[bold cyan]👥 Team Members ({len(members)}):[/bold cyan]")

        # Get detailed member info
        members_table = Table(show_header=True, header_style="bold magenta")
        members_table.add_column("ID", style="dim", width=8)
        members_table.add_column("Name", style="cyan", min_width=15)
        members_table.add_column("Score", style="green", width=10)
        members_table.add_column("Role", style="yellow", width=10)

        total_individual_score = 0
        captain_id = team_data.get('captain_id')

        for member_id in members:
            try:
                # Get individual member details
                member_data = client._make_request('GET', f'/users/{member_id}')
                member_name = member_data.get('name', f'User {member_id}')
                member_score = member_data.get('score', 0)

                role = "Captain" if member_id == captain_id else "Member"

                members_table.add_row(
                    str(member_id),
                    member_name,
                    f"{member_score:,}",
                    role
                )

                total_individual_score += member_score

            except Exception:
                # Fallback if we can't get detailed member info
                role = "Captain" if member_id == captain_id else "Member"
                members_table.add_row(
                    str(member_id),
                    f"User {member_id}",
                    "Unknown",
                    role
                )

        console.print(members_table)

        # Show score breakdown if available
        if total_individual_score > 0:
            console.print(f"\n[cyan]📊 Score Breakdown:[/cyan]")
            console.print(f"  Individual scores total: {total_individual_score:,}")
            console.print(f"  Team score: {team_score:,}")

            if total_individual_score != team_score:
                console.print(f"  [yellow]Note: Team score may include shared challenge points[/yellow]")

    # Get team's solved challenges with member attribution
    try:
        challenges = client.get_challenges()
        solved_challenges = [c for c in challenges if c.solved_by_me]
        challenge_solvers = client.get_challenge_solvers()

        if solved_challenges:
            console.print(f"\n[bold green]🏆 Team Solved Challenges ({len(solved_challenges)}):[/bold green]")

            # Create a detailed table showing who solved what
            challenges_table = Table(show_header=True, header_style="bold magenta")
            challenges_table.add_column("Challenge", style="cyan", min_width=20)
            challenges_table.add_column("Category", style="blue", width=15)
            challenges_table.add_column("Points", style="green", width=8)
            challenges_table.add_column("Solved By", style="yellow", min_width=15)

            # Get member names mapping
            members = team_data.get('members', [])
            member_names = {}
            for member_id in members:
                try:
                    member_data = client._make_request('GET', f'/users/{member_id}')
                    member_names[member_id] = member_data.get('name', f'User {member_id}')
                except Exception:
                    member_names[member_id] = f'User {member_id}'

            total_points = 0
            for challenge in solved_challenges:
                total_points += challenge.value

                # Find who solved this challenge
                solvers = challenge_solvers.get(challenge.id, [])
                if solvers:
                    solver_names = [member_names.get(solver_id, f"User {solver_id}") for solver_id in solvers]
                    solved_by = ", ".join(solver_names)
                else:
                    solved_by = "Unknown"

                challenges_table.add_row(
                    challenge.name,
                    challenge.category,
                    str(challenge.value),
                    solved_by
                )

            console.print(challenges_table)
            console.print(f"\n[green]Total points from solved challenges: {total_points:,}[/green]")

            # Show individual member contributions
            if len(members) > 1:
                console.print(f"\n[bold cyan]👤 Individual Member Contributions:[/bold cyan]")
                member_contributions = {}

                for challenge in solved_challenges:
                    solvers = challenge_solvers.get(challenge.id, [])
                    for solver_id in solvers:
                        if solver_id not in member_contributions:
                            member_contributions[solver_id] = {"challenges": [], "points": 0}
                        member_contributions[solver_id]["challenges"].append(challenge.name)
                        member_contributions[solver_id]["points"] += challenge.value

                contrib_table = Table(show_header=True, header_style="bold magenta")
                contrib_table.add_column("Member", style="cyan", width=15)
                contrib_table.add_column("Challenges Solved", style="green", width=10)
                contrib_table.add_column("Points Contributed", style="yellow", width=15)
                contrib_table.add_column("Challenges", style="blue", min_width=25)

                for member_id in members:
                    member_name = member_names.get(member_id, f'User {member_id}')
                    contrib = member_contributions.get(member_id, {"challenges": [], "points": 0})

                    challenges_list = ", ".join(contrib["challenges"]) if contrib["challenges"] else "None"
                    if len(challenges_list) > 40:
                        challenges_list = challenges_list[:37] + "..."

                    contrib_table.add_row(
                        member_name,
                        str(len(contrib["challenges"])),
                        str(contrib["points"]),
                        challenges_list
                    )

                console.print(contrib_table)

    except Exception as e:
        console.print(f"\n[yellow]Could not fetch solved challenges: {e}[/yellow]")


@app.command("members")
def list_members(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """List team members only."""

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

        team_data = client._make_request('GET', '/teams/me')

        members = team_data.get('members', [])
        captain_id = team_data.get('captain_id')

        if not members:
            console.print("[yellow]No team members found[/yellow]")
            return

        table = Table(title=f"👥 {team_data.get('name', 'Team')} - Members", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", min_width=20)
        table.add_column("Role", style="yellow", width=10)
        table.add_column("Score", style="green", width=10)

        for member_id in members:
            try:
                member_data = client._make_request('GET', f'/users/{member_id}')
                name = member_data.get('name', f'User {member_id}')
                score = member_data.get('score', 0)
                role = "👑 Captain" if member_id == captain_id else "Member"

                table.add_row(name, role, f"{score:,}")

            except Exception:
                role = "👑 Captain" if member_id == captain_id else "Member"
                table.add_row(f"User {member_id}", role, "Unknown")

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch team members: {e}[/red]")
        raise typer.Exit(1)


@app.command("stats")
def team_stats(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Show team statistics and performance."""

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

        team_data = client._make_request('GET', '/teams/me')

        # Get scoreboard for comparison
        scoreboard = client.get_scoreboard(100)
        team_name = team_data.get('name')

        # Find team in scoreboard
        team_entry = None
        for entry in scoreboard:
            if entry.account_name == team_name:
                team_entry = entry
                break

        # Statistics
        stats_table = Table(title=f"📊 {team_name} - Statistics", show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        if team_entry:
            stats_table.add_row("Current Position", f"#{team_entry.pos}")
            stats_table.add_row("Current Score", f"{team_entry.score:,}")

            # Calculate percentile
            total_teams = len(scoreboard)
            percentile = ((total_teams - team_entry.pos + 1) / total_teams) * 100
            stats_table.add_row("Percentile", f"{percentile:.1f}%")

            # Points to next position
            if team_entry.pos > 1:
                next_team = scoreboard[team_entry.pos - 2]  # pos is 1-indexed
                points_needed = next_team.score - team_entry.score + 1
                stats_table.add_row("Points to Next Position", f"{points_needed:,}")

        # Team composition
        members = team_data.get('members', [])
        stats_table.add_row("Team Size", str(len(members)))

        # Solved challenges
        try:
            challenges = client.get_challenges()
            solved = [c for c in challenges if c.solved_by_me]
            total_challenges = len(challenges)
            solve_rate = (len(solved) / total_challenges * 100) if total_challenges > 0 else 0

            stats_table.add_row("Challenges Solved", f"{len(solved)}/{total_challenges}")
            stats_table.add_row("Solve Rate", f"{solve_rate:.1f}%")

        except Exception:
            pass

        console.print(stats_table)

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch team statistics: {e}[/red]")
        raise typer.Exit(1)