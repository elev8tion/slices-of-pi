"""Track B3 — flixz local video path allowlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from pi_orchestrator import database as db
from pi_orchestrator.config import PI_MANAGED_SESSIONS_DIR
from pi_orchestrator.services.flixz_service import (
    FLIXZ_INPUT_DIR,
    _local_video_allowed,
    _path_is_within,
)


class TestFlixzAllowlist:
    def test_path_is_within_child(self, tmp_path: Path):
        child = tmp_path / "v.mp4"
        child.write_text("x")
        assert _path_is_within(tmp_path, child)

    def test_path_not_within_sibling(self, tmp_path: Path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        assert not _path_is_within(a, b)

    def test_allowed_under_flixz_input(self, tmp_path: Path, monkeypatch):
        # Point FLIXZ_INPUT_DIR effectively by putting file under real input dir
        FLIXZ_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        f = FLIXZ_INPUT_DIR / "clip.mp4"
        f.write_bytes(b"fake")
        try:
            assert _local_video_allowed(f, agent_id=None) is True
        finally:
            f.unlink(missing_ok=True)

    def test_disallowed_arbitrary_tmp(self, tmp_path: Path):
        evil = tmp_path / "etc_passwd_copy.mp4"
        evil.write_bytes(b"x")
        # tmp_path is not under ~/.pi allowlist unless env overrides
        assert _local_video_allowed(evil, agent_id=None) is False

    def test_allowed_under_agent_session(self):
        agent = db.create_agent("flixz-path-agent", model="", tools=["read"])
        root = PI_MANAGED_SESSIONS_DIR / agent["name"]
        root.mkdir(parents=True, exist_ok=True)
        video = root / "take.mp4"
        video.write_bytes(b"vid")
        try:
            assert _local_video_allowed(video, agent_id=agent["id"]) is True
        finally:
            video.unlink(missing_ok=True)
