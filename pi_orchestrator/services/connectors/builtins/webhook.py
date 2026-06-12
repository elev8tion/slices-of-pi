"""
Generic Incoming Webhook Connector — easiest custom connector.

Anyone can POST data to an endpoint and it becomes agent knowledge.
No OAuth, no polling — just a URL and a payload.
"""

from __future__ import annotations

from typing import Optional
from .._base import ConnectorPlugin


class WebhookConnector(ConnectorPlugin):
    """Generic incoming webhook connector.

    Configure with a secret token. POST JSON to /api/connectors/webhook/{token}.
    The JSON body becomes a knowledge fact.
    """

    @property
    def provider(self) -> str:
        return "webhook"

    @property
    def display_name(self) -> str:
        return "Incoming Webhook"

    async def authorize(self, config: dict) -> dict:
        token = config.get("token", "")
        if len(token) < 8:
            raise ValueError("Webhook token must be at least 8 characters")
        return {"token": token}

    async def sync(self, auth: dict, since: Optional[str] = None) -> list[dict]:
        return []

    async def verify(self, auth: dict) -> bool:
        return bool(auth.get("token"))
