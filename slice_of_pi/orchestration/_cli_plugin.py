"""
CLI Plugin Interface

Extensible CLI command system. Plugins can register new
commands, subcommands, and configuration profiles for any
backend provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CLIPlugin(ABC):
    """Extensible CLI command system.

    Plugins add commands to the CLI without modifying the core
    CLI tool. Each plugin can register commands, connect to
    profiles, and provide custom output formatting.

    Implementations:
      - DeployPlugin:    Add `deploy` command
      - ChatPlugin:      Add `chat` command
      - MonitorPlugin:   Add `monitor` command
      - SelfUpdatePlugin: Add `update` command
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name, used for --help and logging."""
        ...

    @abstractmethod
    def register_commands(self, app: Any) -> None:
        """Register commands with the CLI application.

        Args:
            app: The CLI framework's application object
                 (click.Group, typer.Typer, argparse, etc.).
                 Type is Any to avoid framework coupling.
        """
        ...

    @abstractmethod
    async def connect(self, profile: str) -> Any:
        """Connect to the agent platform using a named profile.

        Args:
            profile: Named configuration profile (from ~/.slice-of-pi/profiles).

        Returns:
            A client object for interacting with the platform.
        """
        ...
