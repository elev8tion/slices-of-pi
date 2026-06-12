"""
Connector Registry — discover built-in and user-installed connectors.

Scans:
  1. pi_orchestrator.services.connectors.builtins — built-in connectors
  2. ~/.pi/connectors/ — user-installed connector plugins
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Optional

from ._base import ConnectorPlugin

CONNECTORS_DIR = Path.home() / ".pi" / "connectors"

# Module-level cache populated on first call
_registry: dict[str, ConnectorPlugin] = {}


def discover_plugins() -> dict[str, ConnectorPlugin]:
    """Scan builtins and ~/.pi/connectors/ for all ConnectorPlugin classes."""
    plugins = {}

    # 1. Load builtins
    try:
        from .builtins.webhook import WebhookConnector
        for cls in [WebhookConnector]:
            inst = cls()
            plugins[inst.provider] = inst
    except ImportError:
        pass

    # 2. Load user plugins from ~/.pi/connectors/
    if CONNECTORS_DIR.exists():
        for file in sorted(CONNECTORS_DIR.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if isinstance(attr, type) and issubclass(attr, ConnectorPlugin) and attr is not ConnectorPlugin:
                            inst = attr()
                            plugins[inst.provider] = inst
            except Exception as e:
                print(f"Failed to load connector plugin {file.name}: {e}")

    return plugins


def get(provider: str) -> Optional[ConnectorPlugin]:
    """Get a connector plugin by provider name."""
    if not _registry:
        _registry.update(discover_plugins())
    return _registry.get(provider)


def list_available() -> dict[str, dict]:
    """List all available connector plugins (for the dashboard)."""
    if not _registry:
        _registry.update(discover_plugins())
    return {
        name: {
            "provider": plugin.provider,
            "display_name": plugin.display_name,
            "has_schedule": plugin.get_schedule() is not None,
            "schedule": plugin.get_schedule(),
        }
        for name, plugin in _registry.items()
    }


def reload() -> None:
    """Force rediscovery of all plugins. Call after installing a new plugin."""
    _registry.clear()
    _registry.update(discover_plugins())
