"""
ConnectorPlugin — abstract base class for external data connectors.

Each connector syncs data from an external source into the shared
knowledge pool. Connectors are self-contained plugins: anyone can
add one by dropping a .py file in ~/.pi/connectors/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ConnectorPlugin(ABC):
    """Abstract connector for external data sources."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Unique provider name, e.g. 'google-drive', 'custom-slack'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. 'Google Drive'."""
        ...

    @abstractmethod
    async def authorize(self, config: dict) -> dict:
        """Initiate OAuth flow or validate API key.

        Returns auth state dict with tokens, expiry, etc.
        """
        ...

    @abstractmethod
    async def sync(self, auth: dict, since: Optional[str] = None) -> list[dict]:
        """Fetch new/changed content since last sync.

        Returns list of documents:
          [{"id": str, "title": str, "content": str, "url": str,
            "type": str, "updated_at": str}, ...]
        """
        ...

    @abstractmethod
    async def verify(self, auth: dict) -> bool:
        """Check if the connector's auth is still valid."""
        ...

    def get_schedule(self) -> Optional[str]:
        """Cron expression for auto-sync. None = manual only."""
        return None
