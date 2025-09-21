"""Sync challenges and files from CTFd."""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
import typer
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

from ..core import ConfigManager, CTFdClient, Challenge
from ..utils import show_subcommands

app = typer.Typer(help="Sync challenges and files")
console = Console()


def load_sync_metadata(output_dir: Path) -> Dict:
    """Load sync metadata from .ctfdcli directory.

    Args:
        output_dir: Output directory path

    Returns:
        Dictionary containing sync metadata
    """
    metadata_file = output_dir / ".ctfdcli" / "sync_metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"synced_challenges": {}, "last_sync": None, "profile": None}


def save_sync_metadata(output_dir: Path, metadata: Dict):
    """Save sync metadata to .ctfdcli directory.

    Args:
        output_dir: Output directory path
        metadata: Metadata dictionary to save
    """
    metadata_dir = output_dir / ".ctfdcli"
    metadata_dir.mkdir(exist_ok=True)
    metadata_file = metadata_dir / "sync_metadata.json"

    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save sync metadata: {e}[/yellow]")


def detect_challenge_context() -> Optional[int]:
    """Detect if we're in a challenge directory and return challenge ID.

    Returns:
        Challenge ID if in challenge directory, None otherwise
    """
    cwd = Path.cwd()

    # Look for README.md with challenge metadata
    readme_path = cwd / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, 'r') as f:
                content = f.read()
                # Look for challenge ID pattern at the end
                import re
                match = re.search(r'\*Challenge ID: (\d+)', content)
                if match:
                    return int(match.group(1))
        except Exception:
            pass

    return None


def detect_sync_root() -> Optional[Path]:
    """Detect sync root directory by looking for .ctfdcli metadata.

    Returns:
        Path to sync root if found, None otherwise
    """
    current = Path.cwd()

    # Look upwards for .ctfdcli directory
    for parent in [current] + list(current.parents):
        if (parent / ".ctfdcli" / "sync_metadata.json").exists():
            return parent

    return None


def normalize_category_name(category: str) -> str:
    """Normalize category name for filesystem usage.

    Args:
        category: Raw category name

    Returns:
        Filesystem-safe category name
    """
    if not category or not category.strip():
        return "misc"

    # Clean category name for filesystem
    safe_category = category.strip().replace('/', '_').replace('\\', '_').replace(':', '_')
    return safe_category


def normalize_challenge_name(name: str) -> str:
    """Normalize challenge name for filesystem usage.

    Args:
        name: Raw challenge name

    Returns:
        Filesystem-safe challenge name
    """
    return name.replace('/', '_').replace('\\', '_').replace(':', '_')


def create_challenge_readme(challenge: Challenge, challenge_dir: Path):
    """Create comprehensive README.md for a challenge.

    Args:
        challenge: Challenge object
        challenge_dir: Challenge directory path
    """
    # Format challenge type
    challenge_type = challenge.type or "standard"
    type_display = {
        "standard": "Standard",
        "multiple_choice": "Multiple Choice",
        "code": "Code",
        "dynamic": "Dynamic"
    }.get(challenge_type, challenge_type.title())

    # Format status
    status_emoji = "✅" if challenge.solved_by_me else "❌"
    status_text = "SOLVED" if challenge.solved_by_me else "UNSOLVED"

    # Format attempts info
    attempts_info = f"{challenge.attempts}"
    if challenge.max_attempts:
        attempts_info += f"/{challenge.max_attempts}"
        if challenge.attempts >= challenge.max_attempts:
            attempts_info += " ⚠️ LIMIT REACHED"
    else:
        attempts_info += "/∞"

    readme_content = f"""# {challenge.name}

{status_emoji} **Status:** {status_text}
🏷️ **Category:** {challenge.category}
💯 **Points:** {challenge.value}
🎯 **Type:** {type_display}
👥 **Solves:** {challenge.solves}
🔄 **Attempts:** {attempts_info}

## Description

{challenge.description}

## Challenge Details

| Field | Value |
|-------|-------|
| Challenge ID | `{challenge.id}` |
| Category | `{challenge.category}` |
| Points | `{challenge.value}` |
| Type | `{type_display}` |
| State | `{challenge.state}` |
| Max Attempts | `{challenge.max_attempts if challenge.max_attempts else 'Unlimited'}` |
| Current Attempts | `{challenge.attempts}` |

## Tags

{', '.join(f'`{tag}`' for tag in challenge.tags) if challenge.tags else '_No tags_'}

## Connection

"""

    # Add connection information if available
    if challenge.connection_info:
        # Parse connection info using the same function from challenges.py
        from ..commands.challenges import parse_connection_info
        connection = parse_connection_info(challenge.connection_info)
        if connection:
            readme_content += f"**Type:** {connection['icon']} {connection['type'].title()}\n"
            readme_content += f"**Host:** `{connection['host']}`\n"
            readme_content += f"**Port:** `{connection['port']}`\n"
            readme_content += f"**Command:** `{connection['command']}`\n"
        else:
            readme_content += f"**Info:** `{challenge.connection_info}`\n"
    else:
        readme_content += "_No connection information provided_\n"

    readme_content += f"""
## Files

"""

    if challenge.files:
        for file_url in challenge.files:
            filename = file_url.split('/')[-1].split('?')[0]  # Remove query parameters
            readme_content += f"- 📁 `{filename}`\n"
    else:
        readme_content += "_No files provided_\n"

    readme_content += f"""
## Hints

"""

    if challenge.hints:
        for i, hint in enumerate(challenge.hints, 1):
            hint_content = hint.get('content', 'No content') if isinstance(hint, dict) else str(hint)
            readme_content += f"{i}. {hint_content}\n"
    else:
        readme_content += "_No hints available_\n"

    readme_content += f"""
---
*Generated by CTFd CLI*
*Challenge ID: {challenge.id} | Status: {status_text}*
"""

    readme_path = challenge_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Sync challenges from CTFd platform."""
    if ctx.invoked_subcommand is None:
        # Show available subcommands
        subcommands = [
            ("sync", "📥 Sync all challenges from CTFd platform (default action)"),
            ("status", "📊 Show local sync status and statistics"),
        ]

        show_subcommands(
            "sync",
            subcommands,
            "Sync challenges and files from CTFd"
        )


@app.command("sync")
def sync_challenges(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    category: str = typer.Option(None, "--category", "-c", help="Sync only specific category"),
    output_dir: str = typer.Option(None, "--output", "-o", help="Output directory (default: detect from context or 'challenges')"),
    download_files: bool = typer.Option(True, "--files/--no-files", help="Download challenge files"),
    create_readme: bool = typer.Option(True, "--readme/--no-readme", help="Create README files"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
    incremental: bool = typer.Option(True, "--incremental/--full", help="Only sync new/changed challenges"),
    current: bool = typer.Option(False, "--current", help="Sync only the current challenge (if in challenge directory)")
):
    """Sync challenges from CTFd platform."""

    # Handle CWD context detection
    challenge_id_filter = None
    detected_sync_root = None

    if current:
        # User explicitly wants to sync current challenge
        challenge_id_filter = detect_challenge_context()
        if not challenge_id_filter:
            console.print("[red]Not in a challenge directory. Cannot use --current flag.[/red]")
            raise typer.Exit(1)

        # Find sync root
        detected_sync_root = detect_sync_root()
        if not detected_sync_root:
            console.print("[red]Cannot find sync root directory. Run sync from the main challenges directory first.[/red]")
            raise typer.Exit(1)

        console.print(f"[cyan]🎯 Syncing current challenge (ID: {challenge_id_filter})[/cyan]")

    # Determine output directory
    if output_dir is None:
        if detected_sync_root:
            output_dir = str(detected_sync_root)
        elif detect_sync_root():
            output_dir = str(detect_sync_root())
        else:
            output_dir = "challenges"

    config_manager = ConfigManager()
    profile_obj = config_manager.get_profile(profile)

    if not profile_obj:
        if profile:
            console.print(f"[red]Profile '{profile}' not found[/red]")
        else:
            console.print("[red]No default profile found. Run 'ctfdcli init' first.[/red]")
        raise typer.Exit(1)

    # Connect to CTFd
    console.print(f"[cyan]Connecting to {profile_obj.url}...[/cyan]")
    client = CTFdClient(str(profile_obj.url), profile_obj.token)

    try:
        if not client.test_connection():
            console.print("[red]❌ Failed to connect to CTFd[/red]")
            raise typer.Exit(1)

        console.print("[green]✅ Connected successfully[/green]")

        # Get CTF info
        ctf_info = client.get_ctf_info()
        console.print(f"[cyan]Syncing from: {ctf_info.name}[/cyan]")

        # Get challenges
        console.print("[yellow]Fetching challenges...[/yellow]")
        challenges = client.get_challenges()

        if not challenges:
            console.print("[yellow]No challenges found[/yellow]")
            return

        # Filter by specific challenge ID if in --current mode
        if challenge_id_filter:
            challenges = [c for c in challenges if c.id == challenge_id_filter]
            if not challenges:
                console.print(f"[red]Challenge with ID {challenge_id_filter} not found[/red]")
                raise typer.Exit(1)

        # Filter by category if specified
        if category:
            def normalize_category(cat):
                """Normalize category for comparison (empty becomes 'misc')"""
                return (cat.strip() if cat else "misc").lower()

            target_category = normalize_category(category)
            challenges = [c for c in challenges if normalize_category(c.category) == target_category]
            if not challenges:
                console.print(f"[yellow]No challenges found in category '{category}'[/yellow]")
                return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Load sync metadata for incremental sync
        metadata = load_sync_metadata(output_path)
        synced_challenges = metadata.get("synced_challenges", {})

        # Filter challenges for incremental sync
        original_count = len(challenges)
        if incremental and not force:
            new_challenges = []
            for challenge in challenges:
                challenge_key = str(challenge.id)
                stored_challenge = synced_challenges.get(challenge_key, {})

                # Check if challenge needs syncing
                needs_sync = (
                    challenge_key not in synced_challenges or
                    stored_challenge.get("name") != challenge.name or
                    stored_challenge.get("description") != challenge.description or
                    stored_challenge.get("solved_by_me") != challenge.solved_by_me or
                    stored_challenge.get("connection_info") != challenge.connection_info or
                    stored_challenge.get("files") != challenge.files
                )

                if needs_sync:
                    new_challenges.append(challenge)

            challenges = new_challenges

            if original_count > 0 and len(challenges) == 0:
                console.print("[green]✅ All challenges are up to date![/green]")
                return
            elif len(challenges) < original_count:
                console.print(f"[cyan]📦 Incremental sync: {len(challenges)} of {original_count} challenges need updating[/cyan]")

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console
        ) as progress:

            sync_task = progress.add_task(
                f"Syncing {len(challenges)} challenges...",
                total=len(challenges)
            )

            synced_count = 0
            skipped_count = 0
            failed_count = 0

            for challenge in challenges:
                # Solve status is already included in challenge data

                # Use helper functions for normalization
                category_name = normalize_category_name(challenge.category)
                safe_category = category_name
                category_dir = output_path / safe_category
                category_dir.mkdir(exist_ok=True)

                # Create challenge directory
                safe_challenge_name = normalize_challenge_name(challenge.name)
                challenge_dir = category_dir / safe_challenge_name
                challenge_dir.mkdir(exist_ok=True)

                progress.update(
                    sync_task,
                    description=f"Syncing {challenge.name}..."
                )

                try:
                    # Create README if requested
                    if create_readme:
                        readme_path = challenge_dir / "README.md"
                        if not readme_path.exists() or force:
                            create_challenge_readme(challenge, challenge_dir)

                    # Download files if requested
                    if download_files and challenge.files:
                        progress.update(
                            sync_task,
                            description=f"Downloading files for {challenge.name}..."
                        )

                        # Use file URLs directly from challenge data (already have valid tokens)
                        file_urls = []
                        for file in challenge.files:
                            if file.startswith('http'):
                                file_urls.append(file)
                            elif file.startswith('/files/'):
                                file_urls.append(f"{client.base_url}{file}")
                            else:
                                file_path = file.lstrip('/')
                                file_urls.append(f"{client.base_url}/files/{file_path}")

                        downloaded_files = []
                        failed_files = []

                        for file_url in file_urls:
                            # Extract filename from URL (handle query parameters)
                            filename = file_url.split('/')[-1].split('?')[0]
                            if not filename:
                                filename = f"file_{len(downloaded_files)}"

                            local_file_path = challenge_dir / filename

                            if not local_file_path.exists() or force:
                                console.print(f"[cyan]  Downloading {filename}...[/cyan]")
                                try:
                                    if client.download_file(file_url, str(local_file_path)):
                                        downloaded_files.append(filename)
                                        console.print(f"[green]  ✓ Downloaded {filename}[/green]")
                                    else:
                                        failed_files.append(filename)
                                        console.print(f"[yellow]  ✗ Failed to download {filename}[/yellow]")
                                except Exception as e:
                                    failed_files.append(filename)
                                    console.print(f"[red]  ✗ Error downloading {filename}: {e}[/red]")
                            else:
                                downloaded_files.append(filename)
                                console.print(f"[blue]  ≈ Skipped {filename} (already exists)[/blue]")

                        # Summary of file operations
                        if downloaded_files or failed_files:
                            console.print(f"[cyan]  Files for {challenge.name}: {len(downloaded_files)} downloaded, {len(failed_files)} failed[/cyan]")

                    synced_count += 1

                    # Update metadata for successfully synced challenge
                    challenge_key = str(challenge.id)
                    synced_challenges[challenge_key] = {
                        "name": challenge.name,
                        "description": challenge.description,
                        "category": challenge.category,
                        "solved_by_me": challenge.solved_by_me,
                        "connection_info": challenge.connection_info,
                        "files": challenge.files,
                        "last_synced": str(Path().cwd())  # Add timestamp
                    }

                except Exception as e:
                    console.print(f"[red]Failed to sync {challenge.name}: {e}[/red]")
                    failed_count += 1

                progress.update(sync_task, advance=1)

        # Save sync metadata
        from datetime import datetime
        metadata["synced_challenges"] = synced_challenges
        metadata["last_sync"] = datetime.now().isoformat()
        metadata["profile"] = profile_obj.name if hasattr(profile_obj, 'name') else str(profile_obj.url)
        save_sync_metadata(output_path, metadata)

        # Summary
        summary_table = Table(title="📊 Sync Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="green")

        if incremental and original_count > len(challenges):
            summary_table.add_row("Total challenges available", str(original_count))
            summary_table.add_row("Challenges needing sync", str(len(challenges)))
        else:
            summary_table.add_row("Total challenges", str(len(challenges)))

        summary_table.add_row("Successfully synced", str(synced_count))
        if failed_count > 0:
            summary_table.add_row("Failed", str(failed_count))
        summary_table.add_row("Sync mode", "Incremental" if incremental else "Full")
        summary_table.add_row("Output directory", str(output_path.absolute()))

        console.print(summary_table)

        # Show solved challenges
        solved_challenges = [c for c in challenges if c.solved_by_me]
        if solved_challenges:
            console.print(f"\n[green]🎉 You have solved {len(solved_challenges)} challenges![/green]")

        console.print(f"\n[green]✅ Sync completed! Check '{output_path}' directory[/green]")

    except Exception as e:
        console.print(f"[red]❌ Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def sync_status(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use"),
    output_dir: str = typer.Option(None, "--output", "-o", help="Output directory (default: detect from context or 'challenges')")
):
    """Show sync status and statistics."""

    # Handle CWD context detection for status command
    if output_dir is None:
        detected_sync_root = detect_sync_root()
        if detected_sync_root:
            output_dir = str(detected_sync_root)
            console.print(f"[cyan]📍 Auto-detected sync directory: {output_dir}[/cyan]")
        else:
            output_dir = "challenges"

    output_path = Path(output_dir)

    if not output_path.exists():
        console.print(f"[yellow]Output directory '{output_path}' does not exist[/yellow]")
        if detect_sync_root():
            console.print("[yellow]Hint: You might be in a subdirectory. Try running from the main sync directory.[/yellow]")
        return

    # Check if we're in a challenge directory and show context
    current_challenge_id = detect_challenge_context()
    if current_challenge_id:
        console.print(f"[green]📍 Current context: Challenge ID {current_challenge_id}[/green]")

    # Load and display sync metadata if available
    metadata = load_sync_metadata(output_path)
    if metadata.get("last_sync"):
        console.print(f"[cyan]📅 Last sync: {metadata['last_sync']}[/cyan]")
        if metadata.get("profile"):
            console.print(f"[cyan]🔗 Profile: {metadata['profile']}[/cyan]")

    # Count challenges and categories
    categories = []
    total_challenges = 0
    exclude_dirs = {".ctfdcli", "__pycache__", ".git", ".vscode"}

    for category_dir in output_path.iterdir():
        if category_dir.is_dir() and category_dir.name not in exclude_dirs:
            challenge_count = len([d for d in category_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
            if challenge_count > 0:  # Only show categories with challenges
                categories.append((category_dir.name, challenge_count))
                total_challenges += challenge_count

    if not categories:
        console.print("[yellow]No synced challenges found[/yellow]")
        if not metadata.get("last_sync"):
            console.print("[yellow]Hint: Run 'ctfdcli sync sync' to sync challenges first[/yellow]")
        return

    # Status table
    status_table = Table(title="📂 Local Sync Status", show_header=True, header_style="bold magenta")
    status_table.add_column("Category", style="cyan")
    status_table.add_column("Challenges", style="green")

    for category, count in sorted(categories):
        status_table.add_row(category, str(count))

    status_table.add_row("", "")  # Separator
    status_table.add_row("[bold]Total[/bold]", f"[bold]{total_challenges}[/bold]")

    console.print(status_table)

    # Show metadata summary
    if metadata.get("synced_challenges"):
        metadata_count = len(metadata["synced_challenges"])
        if metadata_count != total_challenges:
            console.print(f"[yellow]⚠️ Metadata shows {metadata_count} challenges, but found {total_challenges} directories[/yellow]")

        # Show solved vs unsolved from metadata
        solved_count = sum(1 for c in metadata["synced_challenges"].values() if c.get("solved_by_me", False))
        unsolved_count = metadata_count - solved_count
        console.print(f"[green]✅ Solved: {solved_count}[/green] [red]❌ Unsolved: {unsolved_count}[/red]")

    console.print(f"\n[cyan]📂 Sync directory: {output_path.absolute()}[/cyan]")