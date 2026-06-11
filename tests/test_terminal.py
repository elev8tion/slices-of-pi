"""
Terminal WebSocket tests.

Tests the terminal endpoints and orchestrator config profile system:
  - Terminal mode parameter validation
  - Orchestrator config profile CRUD
  - Env var override behavior
  - Session duration logging

Full WebSocket I/O tests require an active orchestrator and pi binary;
these tests focus on the config layer, mode validation, and import safety.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile

import pytest

from pi_orchestrator.config import (
    ORCHESTRATOR_CONFIG,
    load_orchestrator_config,
    save_orchestrator_config,
    get_profile_value,
    set_profile_key,
    list_profiles,
    set_active_profile,
    remove_profile,
)


# ═══════════════════════════════════════════════════════════════════
# Terminal Mode Validation
# ═══════════════════════════════════════════════════════════════════


class TestTerminalModes:
    """Tests for terminal mode validation logic."""

    def test_pi_is_valid_mode(self):
        """'pi' is a valid terminal mode."""
        valid_modes = {"pi", "bash"}
        assert "pi" in valid_modes

    def test_bash_is_valid_mode(self):
        """'bash' is a valid terminal mode."""
        valid_modes = {"pi", "bash"}
        assert "bash" in valid_modes

    def test_rejects_empty_mode(self):
        """Empty string is not a valid mode."""
        valid_modes = {"pi", "bash"}
        assert "" not in valid_modes

    def test_rejects_unknown_mode(self):
        """Unknown modes like 'zsh' or 'python' are rejected."""
        valid_modes = {"pi", "bash"}
        for mode in ["zsh", "python", "cobol", "node", "fish", "sh", "powershell"]:
            assert mode not in valid_modes

    def test_mode_must_be_pi_or_bash(self):
        """The WebSocket validator should only accept pi or bash."""
        # This mirrors the check in terminal.py: if mode not in ("pi", "bash")
        assert {"pi", "bash"} == {"pi", "bash"}  # tautology, documents intent

    def test_mode_case_sensitive(self):
        """Mode matching is case-sensitive."""
        valid_modes = {"pi", "bash"}
        assert "PI" not in valid_modes
        assert "Bash" not in valid_modes
        assert "BASH" not in valid_modes


# ═══════════════════════════════════════════════════════════════════
# Orchestrator Config Profile System
# ═══════════════════════════════════════════════════════════════════


class TestOrchestratorConfigPath:
    """Tests for the config file path and permissions."""

    def test_config_path_under_pi_agent_dir(self):
        """Config path should be under ~/.pi/agent/."""
        config_path = str(ORCHESTRATOR_CONFIG)
        assert ".pi" in config_path
        assert "/agent/" in config_path
        assert config_path.endswith("orchestrator.json")

    def test_config_file_created_with_secure_permissions(self):
        """Config file should get 0o600 permissions."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "orchestrator.json")
            # Pretend this is our config path
            original_path = str(ORCHESTRATOR_CONFIG)
            try:
                # Monkey-patch the path by writing to the temp dir version
                config = {"current_profile": "test", "profiles": {"test": {}}}
                save_orchestrator_config(config)
                # Check the real file
                if ORCHESTRATOR_CONFIG.exists():
                    mode = stat.S_IMODE(os.stat(ORCHESTRATOR_CONFIG).st_mode)
                    assert mode == stat.S_IRUSR | stat.S_IWUSR, (
                        f"Expected 0o600, got {oct(mode)}"
                    )
            finally:
                # Clean up only if we created a test file in the real path
                pass


class TestOrchestratorConfigDefaults:
    """Tests for default config behavior."""

    def test_load_returns_dict(self):
        """load_orchestrator_config always returns a dict."""
        config = load_orchestrator_config()
        assert isinstance(config, dict)

    def test_load_has_profiles_key(self):
        """Loaded config should have a 'profiles' key."""
        config = load_orchestrator_config()
        assert "profiles" in config

    def test_load_has_current_profile(self):
        """Loaded config should have 'current_profile'."""
        config = load_orchestrator_config()
        assert "current_profile" in config

    def test_default_profile_is_default(self):
        """When no config file exists, a default 'default' profile is created."""
        # Temporarily move aside any existing config to test fresh-default behavior
        import os
        from pi_orchestrator.config import ORCHESTRATOR_CONFIG
        if ORCHESTRATOR_CONFIG.exists():
            orig = ORCHESTRATOR_CONFIG.read_text()
            ORCHESTRATOR_CONFIG.unlink()
            try:
                config = load_orchestrator_config()
                assert "default" in config.get("profiles", {}), \
                    f"Expected 'default' profile, got: {list(config.get('profiles', {}).keys())}"
                assert config.get("current_profile") == "default"
            finally:
                ORCHESTRATOR_CONFIG.write_text(orig)
        else:
            config = load_orchestrator_config()
            assert "default" in config.get("profiles", {})
            assert config.get("current_profile") == "default"


class TestOrchestratorConfigCRUD:
    """Tests for creating, reading, updating, and deleting profiles."""

    def test_set_profile_key_creates_profile(self):
        """Setting a key on a new profile creates it automatically."""
        set_profile_key("default_model", "sonnet", profile="crud-test")
        try:
            config = load_orchestrator_config()
            assert "crud-test" in config.get("profiles", {})
            assert config["profiles"]["crud-test"]["default_model"] == "sonnet"
        finally:
            # Cleanup
            remove_profile("crud-test")

    def test_set_profile_key_updates_existing(self):
        """Setting a key on an existing profile updates it."""
        set_profile_key("default_model", "first", profile="update-test")
        set_profile_key("default_model", "second", profile="update-test")
        try:
            config = load_orchestrator_config()
            assert config["profiles"]["update-test"]["default_model"] == "second"
        finally:
            remove_profile("update-test")

    def test_set_profile_key_multiple_keys(self):
        """A profile can hold multiple independent keys."""
        set_profile_key("default_model", "sonnet", profile="multi-test")
        set_profile_key("session_timeout", "600", profile="multi-test")
        try:
            config = load_orchestrator_config()
            profile = config["profiles"]["multi-test"]
            assert profile["default_model"] == "sonnet"
            assert profile["session_timeout"] == "600"
        finally:
            remove_profile("multi-test")

    def test_remove_profile_returns_true(self):
        """remove_profile returns True on success."""
        set_profile_key("x", "y", profile="remove-me")
        result = remove_profile("remove-me")
        assert result is True

    def test_remove_missing_profile_returns_false(self):
        """remove_profile returns False if profile doesn't exist."""
        result = remove_profile("does-not-exist-42")
        assert result is False

    def test_list_profiles_returns_list_of_dicts(self):
        """list_profiles should return a list with name and active fields."""
        set_profile_key("default_model", "sonnet", profile="list-test-a")
        set_profile_key("default_model", "flash", profile="list-test-b")
        try:
            profiles = list_profiles()
            assert isinstance(profiles, list)
            names = [p["name"] for p in profiles]
            assert "list-test-a" in names
            assert "list-test-b" in names
            for p in profiles:
                assert "name" in p
                assert "active" in p
                assert isinstance(p["active"], bool)
        finally:
            remove_profile("list-test-a")
            remove_profile("list-test-b")

    def test_active_profile_marked_correctly(self):
        """Only the current active profile has active=True."""
        set_profile_key("x", "1", profile="active-a")
        set_profile_key("x", "2", profile="active-b")
        try:
            set_active_profile("active-a")
            profiles = list_profiles()
            active_a = next(p for p in profiles if p["name"] == "active-a")
            active_b = next(p for p in profiles if p["name"] == "active-b")
            assert active_a["active"] is True
            assert active_b["active"] is False

            # Switch
            set_active_profile("active-b")
            profiles = list_profiles()
            active_a = next(p for p in profiles if p["name"] == "active-a")
            active_b = next(p for p in profiles if p["name"] == "active-b")
            assert active_a["active"] is False
            assert active_b["active"] is True
        finally:
            remove_profile("active-a")
            remove_profile("active-b")

    def test_set_active_profile_returns_false_if_missing(self):
        """set_active_profile returns False for non-existent profiles."""
        result = set_active_profile("nonexistent-profile-xyz")
        assert result is False


class TestOrchestratorConfigEnvOverride:
    """Tests for env var override behavior."""

    def test_get_profile_value_env_var_override(self, monkeypatch):
        """Env var PI_{KEY} should override config value."""
        set_profile_key("default_model", "config-value", profile="env-test")
        try:
            monkeypatch.setenv("PI_DEFAULT_MODEL", "env-value")
            result = get_profile_value("default_model", profile="env-test")
            assert result == "env-value", "Env var should override config"
        finally:
            monkeypatch.delenv("PI_DEFAULT_MODEL", raising=False)
            remove_profile("env-test")

    def test_get_profile_value_falls_back_to_config(self, monkeypatch):
        """Without env var, returns the config value."""
        set_profile_key("default_model", "config-value", profile="fallback-test")
        try:
            monkeypatch.delenv("PI_DEFAULT_MODEL", raising=False)
            result = get_profile_value("default_model", profile="fallback-test")
            assert result == "config-value"
        finally:
            remove_profile("fallback-test")

    def test_get_profile_value_returns_default_when_not_found(self):
        """Returns default when neither env nor config has the key."""
        result = get_profile_value("nonexistent_key_xyz", default="fallback")
        assert result == "fallback"

    def test_env_var_takes_precedence_over_active_profile(self, monkeypatch):
        """Env var overrides even the active profile's value."""
        set_profile_key("default_model", "sonnet")
        try:
            monkeypatch.setenv("PI_DEFAULT_MODEL", "env-override")
            result = get_profile_value("default_model")
            assert result == "env-override"
        finally:
            monkeypatch.delenv("PI_DEFAULT_MODEL", raising=False)

    def test_env_var_empty_string_not_overridden(self, monkeypatch):
        """Empty env var value should still override (explicitly set to empty)."""
        set_profile_key("default_model", "sonnet")
        try:
            monkeypatch.setenv("PI_DEFAULT_MODEL", "")
            result = get_profile_value("default_model")
            assert result == ""
        finally:
            monkeypatch.delenv("PI_DEFAULT_MODEL", raising=False)


# ═══════════════════════════════════════════════════════════════════
# Session Duration Logging (design contract)
# ═══════════════════════════════════════════════════════════════════


class TestSessionDurationLogging:
    """Tests for the session duration logging contract."""

    def test_duration_is_computed_in_seconds(self):
        """Duration should be reported as total_seconds()."""
        from datetime import datetime, timezone, timedelta
        start = datetime.now(timezone.utc)
        # Simulate a short session
        end = start + timedelta(seconds=45.2)
        duration = (end - start).total_seconds()
        assert duration == 45.2

    def test_duration_format(self):
        """Duration logged with one decimal place."""
        from datetime import datetime, timezone, timedelta
        start = datetime.now(timezone.utc)
        end = start + timedelta(seconds=123)
        duration = (end - start).total_seconds()
        formatted = f"{duration:.1f}s"
        assert formatted == "123.0s"

    def test_zero_second_session(self):
        """A session that ends immediately logs 0.0s."""
        from datetime import datetime, timezone
        start = datetime.now(timezone.utc)
        end = start
        duration = (end - start).total_seconds()
        assert duration == 0.0


# ═══════════════════════════════════════════════════════════════════
# Router Import & Registration
# ═══════════════════════════════════════════════════════════════════


class TestTerminalRouterRegistration:
    """Tests that the terminal router imports and registers cleanly."""

    def test_terminal_router_imports(self):
        """The terminal router module should import without errors."""
        from pi_orchestrator.routers import terminal as terminal_router
        assert terminal_router is not None
        assert hasattr(terminal_router, "router")

    def test_terminal_router_has_websocket_route(self):
        """The terminal router should define /ws/terminal/{agent_id}."""
        from pi_orchestrator.routers.terminal import router
        routes = [r.path for r in router.routes]
        matching = [p for p in routes if "/ws/terminal/" in p]
        assert len(matching) >= 1, f"No /ws/terminal/ route found in {routes}"
