"""Flag submission commands."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from typing import Optional

from ..core import ConfigManager, CTFdClient
from ..utils import show_subcommands

app = typer.Typer(help="Submit flags")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    challenge_id: int = typer.Argument(None, help="Challenge ID"),
    flag: str = typer.Argument(None, help="Flag to submit"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive flag input")
):
    """Submit a flag for a challenge."""

    if ctx.invoked_subcommand is not None:
        return

    # If no challenge_id provided, show available subcommands
    if challenge_id is None:
        subcommands = [
            ("bulk", "📁 Submit multiple flags from a file"),
            ("history", "📜 Show submission history"),
        ]

        show_subcommands(
            "submit",
            subcommands,
            "Submit flags for challenges\n\nDirect usage: ctfdcli submit <challenge_id> <flag>"
        )
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
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get challenge info first
        challenges = client.get_challenges()
        challenge = next((c for c in challenges if c.id == challenge_id), None)

        if not challenge:
            console.print(f"[red]Challenge with ID {challenge_id} not found[/red]")
            raise typer.Exit(1)

        # Check if already solved
        if challenge.solved_by_me:
            console.print(f"[yellow]⚠️  Challenge '{challenge.name}' is already solved![/yellow]")
            if not typer.confirm("Submit anyway?"):
                return

        # Get flag if not provided
        if not flag:
            if interactive:
                flag = Prompt.ask(
                    f"[cyan]Enter flag for '{challenge.name}' (ID: {challenge_id})[/cyan]",
                    password=True
                )
            else:
                console.print("[red]Flag not provided. Use --interactive or provide flag as argument.[/red]")
                raise typer.Exit(1)

        # Display submission info
        info_table = Table(title="🚩 Flag Submission", show_header=True, header_style="bold magenta")
        info_table.add_column("Field", style="cyan")
        info_table.add_column("Value", style="green")

        info_table.add_row("Challenge", challenge.name)
        info_table.add_row("ID", str(challenge_id))
        info_table.add_row("Category", challenge.category)
        info_table.add_row("Points", str(challenge.value))
        info_table.add_row("Flag", f"{'*' * (len(flag) - 4)}{flag[-4:]}" if len(flag) > 4 else "*" * len(flag))

        console.print(info_table)

        # Submit flag
        console.print("[yellow]Submitting flag...[/yellow]")
        success, message = client.submit_flag(challenge_id, flag)

        if success:
            # Success panel
            success_panel = Panel(
                f"[bold green]🎉 Correct! You solved '{challenge.name}'![/bold green]\n\n"
                f"Points earned: [bold cyan]{challenge.value}[/bold cyan]\n"
                f"Message: {message}",
                title="✅ Flag Accepted",
                border_style="green",
                padding=(1, 2)
            )
            console.print(success_panel)

        else:
            # Failure panel
            failure_panel = Panel(
                f"[bold red]❌ Incorrect flag for '{challenge.name}'[/bold red]\n\n"
                f"Message: {message}\n\n"
                f"[yellow]💡 Tip: Double-check your flag format and try again![/yellow]",
                title="❌ Flag Rejected",
                border_style="red",
                padding=(1, 2)
            )
            console.print(failure_panel)

    except Exception as e:
        console.print(f"[red]❌ Submission failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("bulk")
def bulk_submit(
    file_path: str = typer.Argument(..., help="Path to file with challenge_id:flag pairs"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    delimiter: str = typer.Option(":", "--delimiter", "-d", help="Delimiter for ID:flag pairs"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be submitted without actually submitting")
):
    """Submit multiple flags from a file.

    File format: challenge_id:flag (one per line)
    Example:
    1:flag{example1}
    2:CTF{another_flag}
    """

    import os
    from pathlib import Path

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Check file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        console.print(f"[red]File '{file_path}' not found[/red]")
        raise typer.Exit(1)

    # Read submissions
    submissions = []
    try:
        with open(file_path_obj, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if delimiter not in line:
                    console.print(f"[yellow]Warning: Line {line_num} doesn't contain delimiter '{delimiter}': {line}[/yellow]")
                    continue

                parts = line.split(delimiter, 1)
                if len(parts) != 2:
                    console.print(f"[yellow]Warning: Line {line_num} has invalid format: {line}[/yellow]")
                    continue

                try:
                    challenge_id = int(parts[0].strip())
                    flag = parts[1].strip()
                    submissions.append((challenge_id, flag))
                except ValueError:
                    console.print(f"[yellow]Warning: Line {line_num} has invalid challenge ID: {parts[0]}[/yellow]")
                    continue

    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        raise typer.Exit(1)

    if not submissions:
        console.print("[yellow]No valid submissions found in file[/yellow]")
        return

    console.print(f"[cyan]Found {len(submissions)} submissions to process[/cyan]")

    if dry_run:
        # Show what would be submitted
        table = Table(title="🔍 Dry Run - Submissions", show_header=True, header_style="bold magenta")
        table.add_column("Challenge ID", style="cyan")
        table.add_column("Flag Preview", style="yellow")

        for challenge_id, flag in submissions:
            flag_preview = f"{'*' * (len(flag) - 4)}{flag[-4:]}" if len(flag) > 4 else "*" * len(flag)
            table.add_row(str(challenge_id), flag_preview)

        console.print(table)
        console.print("[cyan]Run without --dry-run to actually submit these flags[/cyan]")
        return

    # Connect to CTFd
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        # Get challenges for validation
        challenges = client.get_challenges()
        challenge_map = {c.id: c for c in challenges}

        # Submit flags
        results = []
        for challenge_id, flag in submissions:
            if challenge_id not in challenge_map:
                results.append((challenge_id, flag, False, "Challenge not found"))
                continue

            challenge = challenge_map[challenge_id]
            console.print(f"[cyan]Submitting flag for '{challenge.name}' (ID: {challenge_id})...[/cyan]")

            success, message = client.submit_flag(challenge_id, flag)
            results.append((challenge_id, flag, success, message))

        # Show results
        results_table = Table(title="📊 Bulk Submission Results", show_header=True, header_style="bold magenta")
        results_table.add_column("Challenge ID", style="cyan")
        results_table.add_column("Challenge Name", style="blue")
        results_table.add_column("Status", style="green")
        results_table.add_column("Message", style="yellow")

        correct_count = 0
        for challenge_id, flag, success, message in results:
            challenge_name = challenge_map.get(challenge_id, {}).name if challenge_id in challenge_map else "Unknown"
            status = "✅ Correct" if success else "❌ Incorrect"

            if success:
                correct_count += 1

            results_table.add_row(
                str(challenge_id),
                challenge_name,
                status,
                message
            )

        console.print(results_table)

        # Summary
        total_submitted = len(results)
        console.print(f"\n[cyan]Summary: {correct_count}/{total_submitted} flags correct ({correct_count/total_submitted*100:.1f}%)[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Bulk submission failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("history")
def submission_history(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of recent submissions to show"),
    challenge_id: Optional[int] = typer.Option(None, "--challenge", "-c", help="Filter by challenge ID")
):
    """Show submission history (if supported by CTFd instance)."""

    console.print("[yellow]Note: Submission history depends on CTFd instance permissions[/yellow]")

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

        # Get challenge details (solve status already included)
        challenges = client.get_challenges()
        solved_challenges = [c for c in challenges if c.solved_by_me]

        if not solved_challenges:
            console.print("[yellow]No solved challenges found[/yellow]")
            return

        # Filter if challenge_id specified
        if challenge_id:
            solved_challenges = [c for c in solved_challenges if c.id == challenge_id]
            if not solved_challenges:
                console.print(f"[yellow]Challenge {challenge_id} not in your solved challenges[/yellow]")
                return

        # Show solved challenges
        table = Table(title="✅ Your Solved Challenges", show_header=True, header_style="bold magenta")
        table.add_column("Challenge ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Category", style="blue")
        table.add_column("Points", style="yellow")

        total_points = 0
        for challenge in solved_challenges[:limit]:
            total_points += challenge.value

            table.add_row(
                str(challenge.id),
                challenge.name,
                challenge.category,
                str(challenge.value)
            )

        console.print(table)
        console.print(f"\n[cyan]Total: {len(solved_challenges)} challenges solved, {total_points} points earned[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Failed to fetch submission history: {e}[/red]")
        raise typer.Exit(1)