"""
Tests for safe Freqtrade command runner behavior.
"""
from pathlib import Path
import subprocess

from app.services.freqtrade_command_runner import FreqtradeCommandRunner


class DummyDetectionService:
    def __init__(self, executable: Path | None, available: bool = True) -> None:
        self.executable = executable
        self.available = available

    def get_freqtrade_executable(self):
        return self.executable

    def is_executable_available(self) -> bool:
        return self.available and self.executable is not None


class FakeLogRepository:
    def __init__(self) -> None:
        self.entries = []

    def add_log(self, **kwargs):
        self.entries.append(kwargs)
        return kwargs


class FakeAuditRepository:
    def __init__(self) -> None:
        self.entries = []

    def create_audit_log(self, data):
        self.entries.append(data)
        return data


def make_runner(executable: Path | None, available: bool = True):
    log_repository = FakeLogRepository()
    audit_repository = FakeAuditRepository()
    runner = FreqtradeCommandRunner(
        detection_service=DummyDetectionService(executable, available),
        log_repository=log_repository,
        audit_repository=audit_repository,
    )
    return runner, log_repository, audit_repository


def test_version_command_allowed(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, audit_repository = make_runner(executable)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="Freqtrade Version:\tfreqtrade 2026.5\n", stderr="")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fake_run)

    result = runner.run_version()

    assert result.success is True
    assert result.command == [str(executable), "--version"]
    assert audit_repository.entries


def test_list_data_command_allowed(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="Found data\n", stderr="")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fake_run)

    result = runner.run(["list-data", "--userdir", "/tmp/user_data"])

    assert result.success is True
    assert result.blocked is False
    assert result.command[:2] == [str(executable), "list-data"]


def test_backtesting_command_allowed_but_mocked(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="Backtesting complete\n", stderr="")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fake_run)

    result = runner.run(["backtesting", "--strategy", "SmokeTestStrategy"])

    assert result.success is True
    assert calls == [[str(executable), "backtesting", "--strategy", "SmokeTestStrategy"]]


def test_trade_command_blocked(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, log_repository, audit_repository = make_runner(executable)

    def fail_run(*args, **kwargs):
        raise AssertionError("blocked commands must not reach subprocess.run")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fail_run)

    result = runner.run(["trade"], run_id="run-1", stage_key="preflight_checks")

    assert result.success is False
    assert result.blocked is True
    assert "Forbidden" in result.error
    assert log_repository.entries[0]["level"] == "warning"
    assert audit_repository.entries[0].approved is False


def test_webserver_command_blocked(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    monkeypatch.setattr(
        "app.services.freqtrade_command_runner.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    result = runner.run(["webserver"])

    assert result.blocked is True
    assert "Forbidden" in result.error


def test_unknown_command_blocked(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    monkeypatch.setattr(
        "app.services.freqtrade_command_runner.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    result = runner.run(["hyperopt"])

    assert result.blocked is True
    assert "Unknown or disallowed" in result.error


def test_shell_operator_blocked(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    monkeypatch.setattr(
        "app.services.freqtrade_command_runner.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    result = runner.run(["list-data", "&&", "cat", ".env"])

    assert result.blocked is True
    assert "Shell operators" in result.error


def test_timeout_handled(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=1, output="TOKEN=abc", stderr="SECRET=def")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", timeout)

    result = runner.run(["list-data"], timeout_seconds=1)

    assert result.success is False
    assert result.timed_out is True
    assert "timed out" in result.error
    assert "abc" not in result.stdout
    assert "def" not in result.stderr


def test_command_logs_are_sanitized(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, log_repository, audit_repository = make_runner(executable)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="DISCORD_BOT_TOKEN=super-secret-token\nok\n",
            stderr="APP_SECRET_KEY=super-secret-key\n",
        )

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fake_run)

    result = runner.run(["list-data", "--api-key", "secret-value"], run_id="run-1")

    assert result.success is True
    assert "super-secret-token" not in result.stdout
    assert "super-secret-key" not in result.stderr
    assert result.sanitized_command[-2:] == ["[REDACTED]", "[REDACTED]"]

    log_body = str(log_repository.entries)
    audit_body = str(audit_repository.entries)
    assert "secret-value" not in log_body
    assert "secret-value" not in audit_body
    assert "super-secret-token" not in log_body
    assert "super-secret-key" not in audit_body


def test_no_shell_true_used(tmp_path, monkeypatch):
    executable = tmp_path / "freqtrade"
    runner, _, _ = make_runner(executable)

    def fake_run(command, **kwargs):
        assert kwargs["shell"] is False
        assert isinstance(command, list)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("app.services.freqtrade_command_runner.subprocess.run", fake_run)

    result = runner.run(["list-strategies"])

    assert result.success is True


def test_missing_freqtrade_returns_controlled_failure():
    runner, _, audit_repository = make_runner(None, available=False)

    result = runner.run(["list-data"])

    assert result.success is False
    assert result.blocked is True
    assert "not configured" in result.error
    assert audit_repository.entries
