"""Deployment contract and a real HTTP startup smoke check."""

import socket
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_and_cool_dependencies_stay_separate():
    cloud = (ROOT / "requirements.txt").read_text()
    app = (ROOT / "requirements-app.txt").read_text()
    installer = (ROOT / "deploy/aws/install_on_cool_ami.sh").read_text()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "-r requirements-app.txt" in cloud
    assert project["project"]["optional-dependencies"]["local"][0] in cloud
    assert all("==" in line for line in app.splitlines() if line and not line.startswith("#"))
    assert not any(
        "opencv" in line.lower() for line in app.splitlines() if line and not line.startswith("#")
    )
    assert "pip install -r requirements-app.txt" in installer
    assert "pip install -r requirements.txt" not in installer
    config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())
    assert "address" not in config["server"]
    service = (ROOT / "deploy/systemd/coolforge.service").read_text()
    assert "--server.address 127.0.0.1" in service


def test_streamlit_server_starts(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
    ]
    log_path = tmp_path / "streamlit.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text(encoding="utf-8"))
                try:
                    with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            assert response.read() == b"ok"
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.2)
            else:
                raise AssertionError("Streamlit health check timed out")
            with urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                assert response.status == 200
                assert b"Streamlit" in response.read()
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
