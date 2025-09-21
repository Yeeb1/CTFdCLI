"""Initialize CTF profile configuration."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text

from ..core import ConfigManager, CTFdClient

app = typer.Typer(help="Initialize CTF profile configuration")
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    name: str = typer.Option(None, "--name", "-n", help="Profile name"),
    url: str = typer.Option(None, "--url", "-u", help="CTFd instance URL"),
    token: str = typer.Option(None, "--token", "-t", help="API access token"),
    user_mode: bool = typer.Option(True, "--user-mode/--team-mode", help="User or team mode"),
    set_default: bool = typer.Option(False, "--default", "-d", help="Set as default profile"),
    test_connection: bool = typer.Option(True, "--test/--no-test", help="Test connection after setup")
):
    """Initialize a new CTF profile with URL and access token."""

    if ctx.invoked_subcommand is not None:
        return

    config_manager = ConfigManager()

    # Welcome banner
    banner = Text("🚩 CTFd CLI Profile Setup", style="bold cyan")
    welcome_panel = Panel(
        banner,
        title="Welcome",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(welcome_panel)

    # Interactive prompts if parameters not provided
    if not name:
        name = Prompt.ask("[cyan]Enter profile name[/cyan]", default="default")

    if not url:
        url = Prompt.ask("[cyan]Enter CTFd instance URL[/cyan]", default="https://demo.ctfd.io")

    if not token:
        console.print("\n[yellow]💡 You can find your API token in CTFd under Settings > Access Tokens[/yellow]")
        token = Prompt.ask("[cyan]Enter API access token[/cyan]", password=True)

    # Ensure URL format
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"

    # Test connection if requested
    if test_connection:
        console.print(f"\n[yellow]Testing connection to {url}...[/yellow]")
        try:
            client = CTFdClient(url, token)
            if client.test_connection():
                console.print("[green]✅ Connection successful![/green]")

                # Get CTF info
                try:
                    ctf_info = client.get_ctf_info()
                    console.print(f"[green]Connected to: {ctf_info.name}[/green]")
                except Exception:
                    pass  # Non-critical error

            else:
                console.print("[red]❌ Connection failed![/red]")
                if not Confirm.ask("Continue anyway?"):
                    raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]❌ Connection error: {e}[/red]")
            if not Confirm.ask("Continue anyway?"):
                raise typer.Exit(1)

    # Check if this is the first profile
    existing_profiles = config_manager.list_profiles()
    is_first_profile = len(existing_profiles) == 0

    if is_first_profile:
        set_default = True
        console.print("[cyan]This will be your default profile (first profile)[/cyan]")
    elif not set_default and existing_profiles:
        set_default = Confirm.ask("Set as default profile?")

    # Add profile
    success = config_manager.add_profile(
        name=name,
        url=url,
        token=token,
        user_mode=user_mode,
        set_default=set_default
    )

    if success:
        # Success message
        success_text = Text("Profile created successfully! 🎉", style="bold green")

        details = []
        details.append(f"Name: {name}")
        details.append(f"URL: {url}")
        details.append(f"Mode: {'User' if user_mode else 'Team'}")
        if set_default:
            details.append("Set as default profile")

        success_panel = Panel(
            success_text + "\n\n" + "\n".join(details),
            title="✅ Success",
            border_style="green",
            padding=(1, 2)
        )
        console.print(success_panel)

        # Next steps
        next_steps = [
            "🔍 List challenges: [cyan]ctfdcli challenges list[/cyan]",
            "📥 Sync challenges: [cyan]ctfdcli sync[/cyan]",
            "🏆 View scoreboard: [cyan]ctfdcli scoreboard[/cyan]",
            "📝 Submit flag: [cyan]ctfdcli submit <challenge_id> <flag>[/cyan]"
        ]

        next_panel = Panel(
            "\n".join(next_steps),
            title="🚀 Next Steps",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(next_panel)

    else:
        console.print("[red]❌ Failed to create profile[/red]")
        raise typer.Exit(1)