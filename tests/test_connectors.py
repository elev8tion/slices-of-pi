"""
Tests for connector plugin system.
"""

from __future__ import annotations

from pi_orchestrator.services.connectors.registry import discover_plugins, list_available, get


class TestPluginDiscovery:
    """Connector plugin discovery should find built-in plugins."""

    def test_discover_builtins(self):
        plugins = discover_plugins()
        assert "webhook" in plugins
        assert plugins["webhook"].provider == "webhook"
        assert plugins["webhook"].display_name == "Incoming Webhook"

    def test_get_webhook_plugin(self):
        plugin = get("webhook")
        assert plugin is not None
        assert plugin.provider == "webhook"

    def test_get_unknown_returns_none(self):
        plugin = get("nonexistent-provider")
        assert plugin is None

    def test_list_available(self):
        available = list_available()
        assert "webhook" in available
        info = available["webhook"]
        assert info["display_name"] == "Incoming Webhook"
        assert info["has_schedule"] is False


class TestWebhookPlugin:
    """Webhook plugin should validate tokens."""

    def test_authorize_valid_token(self):
        import asyncio
        from pi_orchestrator.services.connectors.builtins.webhook import WebhookConnector
        plugin = WebhookConnector()
        result = asyncio.run(plugin.authorize({"token": "my-secret-token-12345"}))
        assert result == {"token": "my-secret-token-12345"}

    def test_authorize_short_token_raises(self):
        import asyncio
        from pi_orchestrator.services.connectors.builtins.webhook import WebhookConnector
        plugin = WebhookConnector()
        try:
            asyncio.run(plugin.authorize({"token": "short"}))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "at least 8 characters" in str(e)

    def test_verify_valid(self):
        import asyncio
        from pi_orchestrator.services.connectors.builtins.webhook import WebhookConnector
        plugin = WebhookConnector()
        assert asyncio.run(plugin.verify({"token": "valid-token-long"}))
        assert not asyncio.run(plugin.verify({}))
