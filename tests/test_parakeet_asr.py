"""Unit tests for Parakeet secondary STT (no full model load in CI)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pi_orchestrator.services import parakeet_asr as pk


def test_resolve_model_dir_default():
    d = pk.resolve_parakeet_model_dir()
    assert "parakeet" in str(d).lower() or "handy" in str(d).lower() or d.name


def test_resolve_model_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_PARAKEET_MODEL_DIR", str(tmp_path))
    assert pk.resolve_parakeet_model_dir() == tmp_path.resolve()


def test_parakeet_available_missing_dir(monkeypatch, tmp_path):
    missing = tmp_path / "nope"
    monkeypatch.setenv("PI_PARAKEET_MODEL_DIR", str(missing))
    ok, detail = pk.parakeet_available()
    assert ok is False
    assert "missing" in detail.lower() or "Model dir" in detail


def test_parakeet_available_incomplete(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_PARAKEET_MODEL_DIR", str(tmp_path))
    (tmp_path / "vocab.txt").write_text("x")
    ok, detail = pk.parakeet_available()
    assert ok is False
    assert "incomplete" in detail.lower() or "missing" in detail.lower()


def test_parakeet_available_complete_no_onnx_asr(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_PARAKEET_MODEL_DIR", str(tmp_path))
    for name in pk.REQUIRED_FILES:
        (tmp_path / name).write_text("{}")
    with patch.object(pk, "_import_onnx_asr", return_value=None), patch.object(
        pk, "_find_parakeet_python", return_value=None
    ):
        ok, detail = pk.parakeet_available()
        assert ok is False
        assert "onnx-asr" in detail.lower() or "install" in detail.lower()


def test_parakeet_available_complete_with_import(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_PARAKEET_MODEL_DIR", str(tmp_path))
    for name in pk.REQUIRED_FILES:
        (tmp_path / name).write_text("{}")
    with patch.object(pk, "_import_onnx_asr", return_value=object()):
        ok, detail = pk.parakeet_available()
        assert ok is True
        assert "in-process" in detail
