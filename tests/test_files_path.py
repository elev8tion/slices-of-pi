"""Track B1 — path containment for agent file manager."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from pi_orchestrator.routers.files import _is_within, _safe_resolve


class TestPathContainment:
    def test_within_same_path(self, tmp_path: Path):
        assert _is_within(tmp_path, tmp_path)

    def test_within_child(self, tmp_path: Path):
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        assert _is_within(tmp_path, child)

    def test_not_within_sibling_prefix(self, tmp_path: Path):
        """Classic startswith bug: base='/data/agent' must not allow '/data/agent_evil'."""
        base = tmp_path / "agent"
        base.mkdir()
        evil = tmp_path / "agent_evil"
        evil.mkdir()
        assert not _is_within(base, evil)

    def test_safe_resolve_allows_relative(self, tmp_path: Path):
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "f.txt").write_text("x")
        got = _safe_resolve(tmp_path, "nested/f.txt")
        assert got == (tmp_path / "nested" / "f.txt").resolve()

    def test_safe_resolve_blocks_traversal(self, tmp_path: Path):
        outside = tmp_path.parent / "outside_secret"
        outside.mkdir(exist_ok=True)
        with pytest.raises(HTTPException) as ei:
            _safe_resolve(tmp_path, "../outside_secret")
        assert ei.value.status_code == 403
