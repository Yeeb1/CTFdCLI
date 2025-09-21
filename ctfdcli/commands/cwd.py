"""CWD (Current Working Directory) commands for challenge operations."""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from ..core import ConfigManager, CTFdClient
from ..utils import show_subcommands

app = typer.Typer(help="Operations within challenge directories")
console = Console()


def find_challenge_info() -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Find challenge information from current directory structure.

    Returns:
        Tuple of (challenge_id, challenge_name, category) or (None, None, None)
    """
    cwd = Path.cwd()

    # Look for README.md with challenge ID
    readme_path = cwd / "README.md"
    if readme_path.exists():
        try:
            content = readme_path.read_text(encoding='utf-8')

            # Extract challenge ID from README
            id_match = re.search(r'Challenge ID.*?`(\d+)`', content)
            if id_match:
                challenge_id = int(id_match.group(1))

                # Get challenge name from title
                title_match = re.search(r'^# (.+)', content, re.MULTILINE)
                challenge_name = title_match.group(1) if title_match else None

                # Try to determine category from directory structure
                category = None
                if cwd.parent.name != "challenges":  # Not in root challenges dir
                    category = cwd.parent.name.replace('_', '/')

                return challenge_id, challenge_name, category

        except Exception:
            pass

    # Fallback: try to infer from directory structure
    # Expected structure: challenges/category/challenge_name/
    parts = cwd.parts
    if len(parts) >= 3 and "challenges" in parts:
        # Find the challenges directory in the path
        try:
            challenges_idx = list(parts).index("challenges")
            if challenges_idx + 2 < len(parts):  # We have category and challenge
                category = parts[challenges_idx + 1].replace('_', '/')
                challenge_name = parts[challenges_idx + 2]
                return None, challenge_name, category
            elif challenges_idx + 1 < len(parts):  # We only have challenge (no category)
                challenge_name = parts[challenges_idx + 1]
                return None, challenge_name, None
        except ValueError:
            pass

    # Final fallback: current directory name as challenge
    if len(parts) >= 1:
        challenge_name = parts[-1]
        return None, challenge_name, None

    return None, None, None


def get_flag_from_file() -> Optional[str]:
    """Get flag content from flag.txt file."""
    flag_path = Path.cwd() / "flag.txt"
    if not flag_path.exists():
        return None

    try:
        content = flag_path.read_text(encoding='utf-8').strip()

        # Remove comments and empty lines
        lines = [line.strip() for line in content.split('\n')
                if line.strip() and not line.strip().startswith('#')]

        if lines:
            return lines[0]  # Return first non-comment line

    except Exception:
        pass

    return None


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Operations within challenge directories."""
    if ctx.invoked_subcommand is None:
        # Show available subcommands
        subcommands = [
            ("info", "ℹ️ Display information about current challenge directory"),
            ("submit", "🚀 Submit flag from current directory (reads flag.txt)"),
        ]

        show_subcommands(
            "cwd",
            subcommands,
            "Perform operations within challenge directories"
        )


@app.command("info")
def challenge_info(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use")
):
    """Display information about the current challenge directory."""

    challenge_id, challenge_name, category = find_challenge_info()

    if not challenge_id and not challenge_name:
        console.print("[red]❌ Not in a challenge directory or unable to detect challenge info[/red]")
        console.print("[yellow]💡 Make sure you're in a directory synced with 'ctfdcli sync'[/yellow]")
        raise typer.Exit(1)

    # Display local directory info
    cwd = Path.cwd()
    info_lines = [
        f"[cyan]📂 Current Directory:[/cyan] {cwd.name}",
        f"[cyan]📍 Full Path:[/cyan] {cwd}",
    ]

    if challenge_name:
        info_lines.append(f"[cyan]🎯 Challenge:[/cyan] {challenge_name}")

    if category:
        info_lines.append(f"[cyan]🏷️ Category:[/cyan] {category}")

    if challenge_id:
        info_lines.append(f"[cyan]🆔 Challenge ID:[/cyan] {challenge_id}")

    # Check for local files
    files = []
    for file_path in cwd.iterdir():
        if file_path.is_file():
            files.append(file_path.name)

    if files:
        info_lines.append(f"[cyan]📁 Local Files:[/cyan] {', '.join(sorted(files))}")

    # Check flag.txt content
    flag_content = get_flag_from_file()
    if flag_content:
        info_lines.append(f"[cyan]🏴 Flag Ready:[/cyan] {flag_content[:20]}..." if len(flag_content) > 20 else f"[cyan]🏴 Flag Ready:[/cyan] {flag_content}")
    else:
        info_lines.append("[yellow]🏴 Flag:[/yellow] No flag in flag.txt")

    directory_panel = Panel(
        "\n".join(info_lines),
        title="📂 Challenge Directory Info",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(directory_panel)

    # Get remote challenge info if we have challenge ID
    if challenge_id:
        config_manager = ConfigManager()
        profile_obj = config_manager.get_profile(profile)

        if profile_obj:
            console.print(f"[cyan]Fetching remote info from {profile_obj.url}...[/cyan]")
            client = CTFdClient(str(profile_obj.url), profile_obj.token)

            try:
                if client.test_connection():
                    challenges = client.get_challenges()
                    challenge = next((c for c in challenges if c.id == challenge_id), None)

                    if challenge:
                        # Display remote challenge info
                        status_emoji = "✅" if challenge.solved_by_me else "❌"
                        status_text = "SOLVED" if challenge.solved_by_me else "UNSOLVED"

                        attempts_info = f"{challenge.attempts}"
                        if challenge.max_attempts:
                            attempts_info += f"/{challenge.max_attempts}"
                            if challenge.attempts >= challenge.max_attempts:
                                attempts_info += " ⚠️ LIMIT REACHED"
                        else:
                            attempts_info += "/∞"

                        remote_info = [
                            f"[cyan]Status:[/cyan] {status_emoji} {status_text}",
                            f"[cyan]Points:[/cyan] {challenge.value}",
                            f"[cyan]Solves:[/cyan] {challenge.solves}",
                            f"[cyan]Attempts:[/cyan] {attempts_info}",
                            f"[cyan]Type:[/cyan] {challenge.type or 'standard'}",
                        ]

                        remote_panel = Panel(
                            "\n".join(remote_info),
                            title="🌐 Remote Challenge Status",
                            border_style="green" if challenge.solved_by_me else "yellow",
                            padding=(1, 2)
                        )
                        console.print(remote_panel)

                        # Show submission warning if attempts are limited
                        if challenge.max_attempts and not challenge.solved_by_me:
                            remaining = challenge.max_attempts - challenge.attempts
                            if remaining <= 3:
                                warning_panel = Panel(
                                    f"⚠️ [bold red]WARNING:[/bold red] Only {remaining} attempts remaining!\n"
                                    f"Use [cyan]ctfdcli cwd submit --confirm[/cyan] for manual confirmation",
                                    title="⚠️ Limited Attempts",
                                    border_style="red",
                                    padding=(1, 2)
                                )
                                console.print(warning_panel)
                    else:
                        console.print(f"[yellow]Challenge ID {challenge_id} not found remotely[/yellow]")
                else:
                    console.print("[yellow]Could not connect to remote CTFd instance[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Could not fetch remote info: {e}[/yellow]")
        else:
            console.print("[yellow]No profile configured for remote info[/yellow]")


@app.command("submit")
def submit_flag(
    flag: str = typer.Option(None, "--flag", "-f", help="Flag to submit (overrides flag.txt)"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    confirm: bool = typer.Option(False, "--confirm", "-c", help="Ask for confirmation before submitting"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be submitted without actually submitting")
):
    """Submit flag from current challenge directory."""

    challenge_id, challenge_name, category = find_challenge_info()

    if not challenge_id:
        console.print("[red]❌ Cannot determine challenge ID from current directory[/red]")
        console.print("[yellow]💡 Make sure you're in a directory synced with 'ctfdcli sync'[/yellow]")
        raise typer.Exit(1)

    # Get flag content
    if flag:
        flag_to_submit = flag
        flag_source = "command line argument"
    else:
        flag_to_submit = get_flag_from_file()
        flag_source = "flag.txt"

        if not flag_to_submit:
            console.print("[red]❌ No flag found in flag.txt and no --flag provided[/red]")
            console.print("[yellow]💡 Add your flag to flag.txt or use --flag option[/yellow]")
            raise typer.Exit(1)

    # Get profile and client
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

        # Get challenge info to check attempts
        challenges = client.get_challenges()
        challenge = next((c for c in challenges if c.id == challenge_id), None)

        if not challenge:
            console.print(f"[red]❌ Challenge ID {challenge_id} not found[/red]")
            raise typer.Exit(1)

        if challenge.solved_by_me:
            console.print("[green]✅ Challenge already solved![/green]")
            return

        # Display submission info
        submission_info = [
            f"[cyan]Challenge:[/cyan] {challenge.name}",
            f"[cyan]Category:[/cyan] {challenge.category}",
            f"[cyan]Points:[/cyan] {challenge.value}",
            f"[cyan]Flag Source:[/cyan] {flag_source}",
            f"[cyan]Flag:[/cyan] {flag_to_submit}",
        ]

        # Check attempts
        attempts_info = f"{challenge.attempts}"
        if challenge.max_attempts:
            attempts_info += f"/{challenge.max_attempts}"
            remaining = challenge.max_attempts - challenge.attempts
            submission_info.append(f"[cyan]Attempts:[/cyan] {attempts_info} ({remaining} remaining)")

            if remaining == 0:
                console.print("[red]❌ No attempts remaining for this challenge[/red]")
                raise typer.Exit(1)
        else:
            attempts_info += "/∞"
            submission_info.append(f"[cyan]Attempts:[/cyan] {attempts_info}")

        submission_panel = Panel(
            "\n".join(submission_info),
            title="🚀 Flag Submission",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(submission_panel)

        # Dry run mode
        if dry_run:
            console.print("[blue]🔍 DRY RUN - No flag submitted[/blue]")
            return

        # Confirmation check
        should_submit = True

        if confirm or (challenge.max_attempts and challenge.max_attempts - challenge.attempts <= 3):
            should_submit = Confirm.ask(
                f"Submit flag '{flag_to_submit}' for challenge '{challenge.name}'?",
                default=True
            )

        if not should_submit:
            console.print("[yellow]❌ Submission cancelled[/yellow]")
            return

        # Submit the flag
        console.print("[cyan]Submitting flag...[/cyan]")
        success, message = client.submit_flag(challenge_id, flag_to_submit)

        if success:
            console.print(f"[green]✅ {message}[/green]")

            # Update local files on success
            flag_path = Path.cwd() / "flag.txt"
            if flag_path.exists() and flag_source == "flag.txt":
                # Add solved marker to flag.txt
                with open(flag_path, 'w', encoding='utf-8') as f:
                    f.write(f"# SOLVED! ✅\n{flag_to_submit}\n")

            # Update README if exists
            readme_path = Path.cwd() / "README.md"
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding='utf-8')
                    # Update status in README
                    content = content.replace("❌ **Status:** UNSOLVED", "✅ **Status:** SOLVED")
                    content = content.replace("**Status:** UNSOLVED", "**Status:** SOLVED")
                    readme_path.write_text(content, encoding='utf-8')
                except Exception:
                    pass  # Ignore README update failures

        else:
            # Show rejection panel similar to main submit command
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