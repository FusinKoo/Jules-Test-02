import os
import logging
import pytest

from mix.model_manager import get_model_path


def _write(path):
    path.write_text("x")
    return str(path)


def test_default_used(monkeypatch, tmp_path):
    default = _write(tmp_path / "G_8200.pth")
    monkeypatch.delenv("RVC_MODEL", raising=False)
    path = get_model_path(default=default, pattern=str(tmp_path / "*.pth"))
    assert path == default


def test_env_overrides_default(monkeypatch, tmp_path):
    default = _write(tmp_path / "G_8200.pth")
    env_model = _write(tmp_path / "env.pth")
    monkeypatch.setenv("RVC_MODEL", env_model)
    path = get_model_path(default=default, pattern=str(tmp_path / "*.pth"))
    assert path == env_model


def test_cli_overrides_env(monkeypatch, tmp_path, caplog):
    default = _write(tmp_path / "G_8200.pth")
    env_model = _write(tmp_path / "env.pth")
    cli_model = _write(tmp_path / "cli.pth")
    monkeypatch.setenv("RVC_MODEL", env_model)
    caplog.set_level(logging.INFO)
    path = get_model_path(cli_path=cli_model, default=default,
                          pattern=str(tmp_path / "*.pth"))
    assert path == cli_model
    assert f"Using model: {cli_model}" in caplog.text


def test_fallback_to_discovery(monkeypatch, tmp_path):
    model_a = _write(tmp_path / "a.pth")
    model_b = _write(tmp_path / "b.pth")
    missing = str(tmp_path / "missing.pth")
    monkeypatch.delenv("RVC_MODEL", raising=False)
    path = get_model_path(default=missing, pattern=str(tmp_path / "*.pth"))
    assert path == model_a


def test_ui_selection(monkeypatch, tmp_path):
    model_a = _write(tmp_path / "a.pth")
    model_b = _write(tmp_path / "b.pth")
    missing = str(tmp_path / "missing.pth")
    monkeypatch.delenv("RVC_MODEL", raising=False)
    monkeypatch.setattr("builtins.input", lambda _: "2")
    path = get_model_path(default=missing, pattern=str(tmp_path / "*.pth"),
                          use_ui=True)
    assert path == model_b


def test_no_model_raises(monkeypatch, tmp_path):
    missing = str(tmp_path / "missing.pth")
    monkeypatch.delenv("RVC_MODEL", raising=False)
    with pytest.raises(FileNotFoundError):
        get_model_path(default=missing, pattern=str(tmp_path / "*.pth"))
