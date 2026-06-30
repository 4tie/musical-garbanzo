"""
Tests for safe Freqtrade detection behavior.
"""
from pathlib import Path
import json
import subprocess

from app.services.freqtrade_detection import FreqtradeDetectionService
from app.services.freqtrade_workspace import FreqtradeWorkspaceService


class DummySettings:
    def __init__(self, root: Path) -> None:
        self._project_root = root
        self.FREQTRADE_PATH = None
        self.FREQTRADE_USER_DATA_DIR = "./freqtrade_workspace/user_data"
        self.FREQTRADE_CONFIG_DIR = "./freqtrade_workspace/config"
        self.FREQTRADE_DEFAULT_CONFIG = "./freqtrade_workspace/config/config.generated.json"
        self.APP_SECRET_KEY = "do-not-expose"
        self.DISCORD_BOT_TOKEN = "also-do-not-expose"

    @property
    def project_root(self) -> Path:
        return self._project_root


def test_detection_returns_missing_status_if_executable_missing(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    workspace = FreqtradeWorkspaceService(settings)
    workspace.ensure_workspace()
    service = FreqtradeDetectionService(settings, workspace)

    monkeypatch.setattr("app.services.freqtrade_detection.shutil.which", lambda _: None)

    status = service.get_status()
    version = service.get_version()

    assert status.configured is False
    assert status.executable_available is False
    assert status.executable_path is None
    assert status.path_source == "missing"
    assert status.workspace_valid is True
    assert "Install Freqtrade" in status.user_action_required
    assert version.available is False


def test_version_command_is_only_command_detection_runs(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    executable = tmp_path / "freqtrade"
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    settings.FREQTRADE_PATH = str(executable)
    workspace = FreqtradeWorkspaceService(settings)
    workspace.ensure_workspace()
    service = FreqtradeDetectionService(settings, workspace)

    calls = []

    def fake_run(command, capture_output, text, timeout, check):
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="Operating System:\tLinux\n\nFreqtrade Version:\tfreqtrade 2026.1\n",
            stderr="",
        )

    monkeypatch.setattr("app.services.freqtrade_detection.subprocess.run", fake_run)

    version = service.get_version()

    assert version.available is True
    assert version.version == "freqtrade 2026.1"
    assert calls == [[str(executable), "--version"]]


def test_detection_uses_freqtrade_from_path_when_no_explicit_path(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    resolved = tmp_path / "bin" / "freqtrade"
    resolved.parent.mkdir()
    resolved.write_text("#!/bin/sh\n")
    resolved.chmod(0o755)
    workspace = FreqtradeWorkspaceService(settings)
    workspace.ensure_workspace()
    service = FreqtradeDetectionService(settings, workspace)

    monkeypatch.setattr("app.services.freqtrade_detection.shutil.which", lambda _: str(resolved))

    assert service.get_freqtrade_executable() == resolved
    assert service.is_configured() is True
    assert service.is_executable_available() is True


def test_missing_explicit_executable_is_controlled_status(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    settings.FREQTRADE_PATH = str(tmp_path / "missing-freqtrade")
    workspace = FreqtradeWorkspaceService(settings)
    workspace.ensure_workspace()
    service = FreqtradeDetectionService(settings, workspace)

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for missing executable")

    monkeypatch.setattr("app.services.freqtrade_detection.subprocess.run", fail_run)

    version = service.get_version()
    status = service.get_status()

    assert version.available is False
    assert "not available" in version.error
    assert status.configured is True
    assert status.executable_available is False
    assert status.path_source == "configured"


def test_detection_status_does_not_expose_secret_settings(tmp_path, monkeypatch):
    settings = DummySettings(tmp_path)
    workspace = FreqtradeWorkspaceService(settings)
    workspace.ensure_workspace()
    service = FreqtradeDetectionService(settings, workspace)

    monkeypatch.setattr("app.services.freqtrade_detection.shutil.which", lambda _: None)

    body = json.dumps(service.get_status().model_dump()).lower()

    assert "do-not-expose" not in body
    assert "also-do-not-expose" not in body
    assert "discord_bot_token" not in body
    assert "app_secret_key" not in body
