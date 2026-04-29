from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import paramiko
import pytest

from diode_metrics_exporter.sftp_client import ParamikoSFTPClient


def test_connect(monkeypatch: pytest.MonkeyPatch):
    fake_ssh = MagicMock()

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(
        host="localhost", port=22, username="user", password="pass"
    )

    client.connect()

    fake_ssh.load_system_host_keys.assert_called_once()
    fake_ssh.connect.assert_called_once_with(
        hostname="localhost", port=22, username="user", password="pass"
    )

    fake_ssh.open_sftp.assert_called_once()


def test_list_files(monkeypatch: pytest.MonkeyPatch):
    fake_sftp = MagicMock()
    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    fake_sftp.listdir_attr.return_value = [
        SimpleNamespace(filename="a.csv", st_mtime=100, st_size=10),
        SimpleNamespace(filename="b.csv", st_mtime=200, st_size=20),
    ]

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(host="x", port=22, username="u", password="p")

    client.connect()

    files = client.list_files("/incoming")

    assert len(files) == 2
    assert files[0].name == "a.csv"
    assert files[1].name == "b.csv"

    fake_sftp.listdir_attr.assert_called_once_with("/incoming")


def test_download_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    fake_sftp = MagicMock()
    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(host="x", port=22, username="u", password="p")

    client.connect()

    local_file = tmp_path / "file.csv"

    client.download_file("/remote/file.csv", local_file)

    fake_sftp.get.assert_called_once_with("/remote/file.csv", str(local_file))


def test_delete_file(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sftp = MagicMock()
    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(
        host="localhost",
        port=22,
        username="user",
        password="pass",
    )

    client.connect()

    client.delete_file("/incoming/HEALTHCHECK")

    fake_sftp.remove.assert_called_once_with("/incoming/HEALTHCHECK")


def test_close(monkeypatch: pytest.MonkeyPatch):
    fake_sftp = MagicMock()
    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(host="x", port=22, username="u", password="p")

    client.connect()
    client.close()

    fake_sftp.close.assert_called_once()
    fake_ssh.close.assert_called_once()


def test_read_bytes_reads_expected_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_file = MagicMock()
    fake_file.read.return_value = b"\x1f\x8b"
    fake_file.__enter__.return_value = fake_file
    fake_file.__exit__.return_value = None

    fake_sftp = MagicMock()
    fake_sftp.open.return_value = fake_file

    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient(
        host="localhost",
        port=22,
        username="user",
        password="pass",
    )

    client.connect()

    result = client.read_bytes(
        remote_path="/incoming/report.tar.gz",
        size=2,
        offset=0,
    )

    assert result == b"\x1f\x8b"

    fake_sftp.open.assert_called_once_with(
        "/incoming/report.tar.gz",
        "rb",
    )
    fake_file.seek.assert_called_once_with(0)
    fake_file.read.assert_called_once_with(2)


def test_read_bytes_uses_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_file = MagicMock()
    fake_file.read.return_value = b"ustar"
    fake_file.__enter__.return_value = fake_file
    fake_file.__exit__.return_value = None

    fake_sftp = MagicMock()
    fake_sftp.open.return_value = fake_file

    fake_ssh = MagicMock()
    fake_ssh.open_sftp.return_value = fake_sftp

    monkeypatch.setattr(paramiko, "SSHClient", lambda: fake_ssh)

    client = ParamikoSFTPClient("localhost", 22, "user", "pass")
    client.connect()

    result = client.read_bytes(
        remote_path="/incoming/report.tar",
        size=5,
        offset=257,
    )

    assert result == b"ustar"
    fake_file.seek.assert_called_once_with(257)
    fake_file.read.assert_called_once_with(5)


def test_read_bytes_raises_when_not_connected() -> None:
    client = ParamikoSFTPClient("localhost", 22, "user", "pass")

    with pytest.raises(RuntimeError, match="SFTP client not connected"):
        client.read_bytes("/incoming/report.tar.gz", size=2)
