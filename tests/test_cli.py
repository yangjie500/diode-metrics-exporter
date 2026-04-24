import subprocess
import sys

from diode_metrics_exporter import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "diode_metrics_exporter", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
