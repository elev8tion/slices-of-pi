"""
Channel Adapter Interface

Abstract adapter for external message channels.

Agents can communicate through many channels: Slack, Discord,
Telegram, WhatsApp, Microsoft Teams, webhooks, email, SMS.

Each channel has its own protocol, authentication, and message
format. This interface abstracts those differences so the
orchestrator can route messages uniformly.

Architecture:
  Orchestrator → MessageRouter → [ChannelAdapter for each channel]
                                   ↓
                              External platform
                                   ↓
                              [Incoming webhook] → ChannelAdapter → MessageRouter → Agent
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional

# Incoming message handler: async callable receiving (sender, content, thread_id)
MessageHandler = Callable[[str, str, Optional[str]], Awaitable[None]]


class ChannelAdapter(ABC):
    """Abstract adapter for external message channels.

    Implement one of these for each messaging platform your agents
    need to connect to. The adapter handles platform-specific auth,
    message formatting, attachment handling, and event streaming.

    Implementations:
      - SlackAdapter     — Slack Events API + Socket Mode
      - TelegramAdapter  — Telegram Bot API
      - DiscordAdapter   — Discord Gateway
      - WhatsAppAdapter  — Twilio/WhatsApp Business API
      - WebhookAdapter   — Generic incoming webhook
    """

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Platform identifier, e.g. 'slack', 'telegram', 'discord'."""
        ...

    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> None:
        """Connect to the messaging platform.

        Args:
            config: Platform-specific connection config
                    (tokens, webhook URLs, signing secrets, etc.).
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the messaging platform.

        Clean up connections, close websockets, cancel listeners.
        Must be idempotent.
        """
        ...

    @abstractmethod
    async def send_message(
        self,
        recipient: str,
        content: str,
        thread_id: Optional[str] = None,
    ) -> str:
        """Send a message through the channel.

        Args:
            recipient: Channel/user/group ID (platform-specific).
            content:   Message text (may include platform markup).
            thread_id: Thread to reply in (optional).

        Returns:
            Platform-assigned message ID.
        """
        ...

    @abstractmethod
    async def on_message(self, handler: MessageHandler) -> None:
        """Register a callback for incoming messages.

        The handler receives (sender_id, content, thread_id) and
        should return nothing. Errors in the handler should be
        caught by the adapter and logged — they must not crash
        the connection loop.
        """
        ...

    # ------------------------------------------------------------------ optional

    async def send_file(
        self,
        recipient: str,
        file_path: str,
        caption: Optional[str] = None,
    ) -> str:
        """Send a file through the channel.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError

    async def typing_indicator(
        self,
        recipient: str,
        active: bool = True,
    ) -> None:
        """Show/hide a typing indicator.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError
