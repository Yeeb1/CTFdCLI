"""Configuration management for CTFd CLI."""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console

from .models import CTFProfile


class ConfigManager:
    """Manages CTF profiles and configuration."""

    def __init__(self):
        """Initialize configuration manager."""
        self.console = Console()
        self.config_dir = self._get_config_directory()
        self.config_file = self.config_dir / "profiles.json"
        self.ensure_config_directory()

    def _get_config_directory(self) -> Path:
        """Get configuration directory path.

        Returns:
            Configuration directory path
        """
        # Try local config first, then user config
        local_config = Path.cwd() / ".ctfdcli"
        if local_config.exists():
            return local_config

        user_config = Path.home() / ".ctfdcli"
        return user_config

    def ensure_config_directory(self):
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(exist_ok=True)

    def load_profiles(self) -> Dict[str, CTFProfile]:
        """Load all profiles from configuration.

        Returns:
            Dictionary of profile name to profile
        """
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)

            profiles = {}
            for name, profile_data in data.items():
                profiles[name] = CTFProfile(**profile_data)

            return profiles

        except (json.JSONDecodeError, ValueError) as e:
            self.console.print(f"[red]Error loading profiles: {e}[/red]")
            return {}

    def save_profiles(self, profiles: Dict[str, CTFProfile]):
        """Save profiles to configuration.

        Args:
            profiles: Dictionary of profiles to save
        """
        try:
            data = {}
            for name, profile in profiles.items():
                data[name] = profile.model_dump()

            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            self.console.print(f"[red]Error saving profiles: {e}[/red]")
            raise

    def add_profile(
        self,
        name: str,
        url: str,
        token: str,
        user_mode: bool = True,
        set_default: bool = False
    ) -> bool:
        """Add a new profile.

        Args:
            name: Profile name
            url: CTFd URL
            token: API token
            user_mode: True for user mode, False for team mode
            set_default: Whether to set as default profile

        Returns:
            True if successful, False otherwise
        """
        try:
            profiles = self.load_profiles()

            # Clear other defaults if setting this as default
            if set_default:
                for profile in profiles.values():
                    profile.default = False

            # Create new profile
            profile = CTFProfile(
                name=name,
                url=url,
                token=token,
                user_mode=user_mode,
                default=set_default or len(profiles) == 0  # First profile is default
            )

            profiles[name] = profile
            self.save_profiles(profiles)

            return True

        except Exception as e:
            self.console.print(f"[red]Error adding profile: {e}[/red]")
            return False

    def get_profile(self, name: Optional[str] = None) -> Optional[CTFProfile]:
        """Get a profile by name or default profile.

        Args:
            name: Profile name (None for default)

        Returns:
            Profile or None if not found
        """
        profiles = self.load_profiles()

        if name:
            return profiles.get(name)

        # Find default profile
        for profile in profiles.values():
            if profile.default:
                return profile

        # Return first profile if no default set
        if profiles:
            return next(iter(profiles.values()))

        return None

    def list_profiles(self) -> List[CTFProfile]:
        """List all profiles.

        Returns:
            List of all profiles
        """
        profiles = self.load_profiles()
        return list(profiles.values())

    def delete_profile(self, name: str) -> bool:
        """Delete a profile.

        Args:
            name: Profile name to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            profiles = self.load_profiles()

            if name not in profiles:
                self.console.print(f"[red]Profile '{name}' not found[/red]")
                return False

            # Check if deleting default profile
            was_default = profiles[name].default
            del profiles[name]

            # Set new default if we deleted the default profile
            if was_default and profiles:
                first_profile = next(iter(profiles.values()))
                first_profile.default = True

            self.save_profiles(profiles)
            return True

        except Exception as e:
            self.console.print(f"[red]Error deleting profile: {e}[/red]")
            return False

    def set_default_profile(self, name: str) -> bool:
        """Set a profile as default.

        Args:
            name: Profile name to set as default

        Returns:
            True if successful, False otherwise
        """
        try:
            profiles = self.load_profiles()

            if name not in profiles:
                self.console.print(f"[red]Profile '{name}' not found[/red]")
                return False

            # Clear all defaults and set new one
            for profile in profiles.values():
                profile.default = False
            profiles[name].default = True

            self.save_profiles(profiles)
            return True

        except Exception as e:
            self.console.print(f"[red]Error setting default profile: {e}[/red]")
            return False

    def get_workspace_directory(self, profile_name: str) -> Path:
        """Get workspace directory for a profile.

        Args:
            profile_name: Profile name

        Returns:
            Workspace directory path
        """
        workspace_dir = self.config_dir / "workspaces" / profile_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir