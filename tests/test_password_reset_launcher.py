"""Verify recovery launcher arguments without touching a real Docker deployment."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows recovery launcher")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def installation(tmp_path: Path) -> Path:
    root = tmp_path / "recovery with spaces"
    (root / "scripts").mkdir(parents=True)
    for relative in ("scripts/reset-admin-password.ps1", "scripts/reset_admin_password.py"):
        shutil.copyfile(ROOT / relative, root / relative)
    (root / "docker.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0fake_docker.py" %*\n', encoding="utf-8"
    )
    (root / "fake_docker.py").write_text(
        "import ast, base64, json, pathlib, sys\n"
        "root = pathlib.Path(__file__).parent\n"
        "args = sys.argv[1:]\n"
        "runner = ast.parse(args[args.index('-c') + 1])\n"
        "payload = runner.body[1].value.args[0].args[0].value\n"
        "ast.parse(base64.b64decode(payload))\n"
        "(root / 'call.json').write_text(json.dumps(args))\n"
        "sys.exit(17 if (root / 'fail').exists() else 0)\n",
        encoding="utf-8",
    )
    return root


def launch(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "scripts/reset-admin-password.ps1"),
            *arguments,
        ],
        cwd=root.parent,
        env={**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("Auto", "docker-compose.home.yml"),
        ("Home", "docker-compose.home.yml"),
        ("Local", "docker-compose.yml"),
    ],
)
def test_recovery_selects_stack_and_keeps_configuration(
    installation: Path, mode: str, expected: str
) -> None:
    for filename in (".env", ".env.home"):
        (installation / filename).write_text("EXISTING=keep-me\n", encoding="utf-8")
    result = launch(installation, "-Mode", mode, "-StudentNo", "owner")
    assert result.returncode == 0, result.stdout + result.stderr
    args = json.loads((installation / "call.json").read_text())
    assert args[args.index("-f") + 1].endswith(expected)
    assert args[args.index("exec") + 1 : args.index("-c")] == ["backend", ".venv/bin/python"]
    assert args[-1] == "owner"
    assert "-T" not in args and "up" not in args and "--build" not in args
    for filename in (".env", ".env.home"):
        assert (installation / filename).read_text() == "EXISTING=keep-me\n"


def test_auto_uses_local_deployment_when_no_home_config_exists(installation: Path) -> None:
    (installation / ".env").write_text("EXISTING=keep-me\n", encoding="utf-8")
    result = launch(installation)
    assert result.returncode == 0, result.stdout + result.stderr
    args = json.loads((installation / "call.json").read_text())
    assert args[args.index("-f") + 1].endswith("docker-compose.yml")
    assert args[-1] == "admin"
    assert not (installation / ".env.home").exists()


def test_recovery_reports_container_failure(installation: Path) -> None:
    (installation / ".env.home").write_text("EXISTING=keep-me\n", encoding="utf-8")
    (installation / "fail").touch()
    result = launch(installation)
    assert result.returncode == 1
    assert "Password reset failed or was cancelled" in result.stdout


def test_recovery_does_not_create_missing_configuration(installation: Path) -> None:
    result = launch(installation, "-Mode", "Home")
    assert result.returncode == 1
    assert ".env.home is missing" in result.stdout
    assert not (installation / ".env.home").exists()
    assert not (installation / "call.json").exists()
