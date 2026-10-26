"""Exercise the real PowerShell launcher with isolated files and fake external services."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def installation(tmp_path: Path) -> Path:
    root = tmp_path / "installation with spaces"
    (root / "scripts" / "home").mkdir(parents=True)
    for relative in (
        "scripts/launcher.ps1",
        "scripts/home/init-home-env.ps1",
        ".env.example",
        ".env.home.example",
        "docker-compose.yml",
        "docker-compose.home.yml",
    ):
        shutil.copyfile(ROOT / relative, root / relative)
    (root / "fake_docker.py").write_text(
        "import json, pathlib, sys\n"
        "root = pathlib.Path(__file__).parent\n"
        "with (root / 'calls.jsonl').open('a') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if 'up' in sys.argv and (root / 'fail').exists():\n"
        "    sys.exit(17)\n",
        encoding="utf-8",
    )
    (root / "docker.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0fake_docker.py" %*\n', encoding="utf-8"
    )
    return root


def launch(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    script = str(root / "scripts" / "launcher.ps1").replace("'", "''")
    # HTTP calls are external boundaries; no running service or user's containers are touched.
    command = (
        "function global:Invoke-RestMethod { @{data=@{status='ok'}} }; "
        "function global:Invoke-WebRequest { @{StatusCode=200} }; "
        f"& '{script}' -NoBrowser " + " ".join(arguments)
    )
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=root.parent,
        env={**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=45,
    )


def compose_calls(root: Path) -> list[list[str]]:
    calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
    return [call for call in calls if "--project-directory" in call]


def test_start_creates_missing_local_config_and_reuses_it(installation: Path) -> None:
    first = launch(installation, "-Rebuild")
    assert first.returncode == 0, first.stdout + first.stderr
    env_path = installation / ".env"
    assert "BOOTSTRAP_ADMIN_PASSWORD=BookPath@123" in env_path.read_text()
    calls = compose_calls(installation)
    assert calls[-1][-3:] == ["up", "-d", "--build"]
    assert calls[-1][calls[-1].index("-f") + 1].endswith("docker-compose.yml")

    env_path.write_text("CUSTOM_SETTING=keep-me\n", encoding="utf-8")
    second = launch(installation)
    assert second.returncode == 0, second.stdout + second.stderr
    assert env_path.read_text() == "CUSTOM_SETTING=keep-me\n"
    assert compose_calls(installation)[-1][-2:] == ["up", "-d"]


def test_auto_uses_existing_home_config_and_stop_preserves_data(installation: Path) -> None:
    home_env = installation / ".env.home"
    home_env.write_text("EXISTING_SECRET=unchanged\n", encoding="utf-8")
    (installation / ".env").write_text("LOCAL_CONFIG=unchanged\n", encoding="utf-8")
    started = launch(installation)
    assert started.returncode == 0, started.stdout + started.stderr
    stopped = launch(installation, "-Action Stop")
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    assert home_env.read_text() == "EXISTING_SECRET=unchanged\n"
    calls = compose_calls(installation)
    assert all("docker-compose.home.yml" in call[call.index("-f") + 1] for call in calls)
    assert calls[-1][-1] == "stop"
    assert all("-v" not in call and "down" not in call for call in calls)


def test_explicit_home_generates_random_initial_password(installation: Path) -> None:
    result = launch(installation, "-Mode Home")
    assert result.returncode == 0, result.stdout + result.stderr
    values = dict(
        line.split("=", 1)
        for line in (installation / ".env.home").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    assert len(values["BOOTSTRAP_ADMIN_PASSWORD"]) == 16
    assert values["BOOTSTRAP_ADMIN_PASSWORD"] != "__ADMIN_PASSWORD__"
    assert values["BOOTSTRAP_ADMIN_PASSWORD"] not in result.stdout


def test_compose_failure_is_reported_as_failure(installation: Path) -> None:
    (installation / "fail").touch()
    result = launch(installation)
    assert result.returncode == 1
    assert "Docker Compose failed (exit 17)" in result.stdout
    assert "Ready:" not in result.stdout
