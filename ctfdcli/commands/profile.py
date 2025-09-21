"""Profile management commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm

from ..core import ConfigManager
from ..utils import show_subcommands

app = typer.Typer(help="Manage CTF profiles")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Manage CTF profiles."""
    if ctx.invoked_subcommand is None:
        # Show available subcommands
        subcommands = [
            ("list", "📋 List all configured profiles"),
            ("show", "👁️  Show detailed information about a profile"),
            ("delete", "🗑️  Delete a profile"),
            ("set-default", "⭐ Set a profile as the default"),
            ("test", "🔌 Test connection to a profile's CTFd instance"),
        ]

        show_subcommands(
            "profile",
            subcommands,
            "Manage your CTF platform profiles"
        )


@app.command("list")
def list_profiles():
    """List all configured profiles."""
    config_manager = ConfigManager()
    profiles = config_manager.list_profiles()

    if not profiles:
        console.print("[yellow]No profiles configured. Run 'ctfdcli init' to create one.[/yellow]")
        return

    table = Table(title="🔧 CTF Profiles", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("URL", style="blue", width=40)
    table.add_column("Mode", style="green", width=10)
    table.add_column("Default", style="yellow", width=10)

    for profile in profiles:
        default_marker = "✅" if profile.default else ""
        mode = "User" if profile.user_mode else "Team"

        table.add_row(
            profile.name,
            str(profile.url),
            mode,
            default_marker
        )

    console.print(table)


@app.command("show")
def show_profile(
    name: str = typer.Argument(None, help="Profile name (default profile if not specified)")
):
    """Show detailed information about a profile."""
    config_manager = ConfigManager()
    profile = config_manager.get_profile(name)

    if not profile:
        if name:
            console.print(f"[red]Profile '{name}' not found[/red]")
        else:
            console.print("[red]No default profile found[/red]")
        raise typer.Exit(1)

    # Create detailed info panel
    details = []
    details.append(f"[cyan]Name:[/cyan] {profile.name}")
    details.append(f"[cyan]URL:[/cyan] {profile.url}")
    details.append(f"[cyan]Mode:[/cyan] {'User' if profile.user_mode else 'Team'}")
    details.append(f"[cyan]Default:[/cyan] {'Yes' if profile.default else 'No'}")
    details.append(f"[cyan]Token:[/cyan] {'*' * 20}...{profile.token[-10:]}")

    info_panel = Panel(
        "\n".join(details),
        title=f"📋 Profile: {profile.name}",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(info_panel)


@app.command("delete")
def delete_profile(
    name: str = typer.Argument(..., help="Profile name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """Delete a profile."""
    config_manager = ConfigManager()

    # Check if profile exists
    profile = config_manager.get_profile(name)
    if not profile:
        console.print(f"[red]Profile '{name}' not found[/red]")
        raise typer.Exit(1)

    # Confirmation
    if not force:
        if not Confirm.ask(f"Are you sure you want to delete profile '{name}'?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Delete profile
    if config_manager.delete_profile(name):
        console.print(f"[green]✅ Profile '{name}' deleted successfully[/green]")
    else:
        console.print(f"[red]❌ Failed to delete profile '{name}'[/red]")
        raise typer.Exit(1)


@app.command("set-default")
def set_default_profile(
    name: str = typer.Argument(..., help="Profile name to set as default")
):
    """Set a profile as the default."""
    config_manager = ConfigManager()

    if config_manager.set_default_profile(name):
        console.print(f"[green]✅ Profile '{name}' set as default[/green]")
    else:
        raise typer.Exit(1)


@app.command("test")
def test_profile(
    name: str = typer.Argument(None, help="Profile name (default profile if not specified)")
):
    """Test connection to a profile's CTFd instance."""
    from ..core import CTFdClient

    config_manager = ConfigManager()
    profile = config_manager.get_profile(name)

    if not profile:
        if name:
            console.print(f"[red]Profile '{name}' not found[/red]")
        else:
            console.print("[red]No default profile found[/red]")
        raise typer.Exit(1)

    console.print(f"[yellow]Testing connection to {profile.url}...[/yellow]")

    try:
        client = CTFdClient(str(profile.url), profile.token)

        if client.test_connection():
            console.print("[green]✅ Connection successful![/green]")

            # Get additional info
            try:
                ctf_info = client.get_ctf_info()
                me = client.get_me()

                info_lines = [f"CTF Name: {ctf_info.name}"]
                if me:
                    info_lines.append(f"Logged in as: {me.name}")
                    info_lines.append(f"Score: {me.score}")

                info_panel = Panel(
                    "\n".join(info_lines),
                    title="📊 Connection Info",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(info_panel)

            except Exception as e:
                console.print(f"[yellow]Connected but couldn't fetch details: {e}[/yellow]")

        else:
            console.print("[red]❌ Connection failed![/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Connection error: {e}[/red]")
        raise typer.Exit(1)