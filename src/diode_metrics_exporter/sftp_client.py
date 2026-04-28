from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import paramiko


@dataclass(frozen=True)
class RemoteFile:
    name: str
    mtime: int
    size: int


class SFTPClient(Protocol):
    def list_files(self, remote_dir: str) -> list[RemoteFile]: ...

    def download_file(self, remote_path: str, local_path: Path) -> None: ...

    def delete_file(self, remote_path: str) -> None: ...

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes: ...


class ParamikoSFTPClient:
    def __init__(
        self, host: str, port: int, username: str, password: str | None = None
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssh: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.load_system_host_keys()
        self._ssh.set_missing_host_key_policy(paramiko.RejectPolicy())

        self._ssh.connect(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
        )

        self._sftp = self._ssh.open_sftp()

    def list_files(self, remote_dir: str) -> list[RemoteFile]:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        entries = self._sftp.listdir_attr(remote_dir)

        files: list[RemoteFile] = []
        for entry in entries:
            files.append(
                RemoteFile(
                    name=entry.filename,
                    mtime=entry.st_mtime or 0,
                    size=entry.st_size or 0,
                )
            )

        return files

    def download_file(self, remote_path: str, local_path: Path):
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        self._sftp.get(remote_path, str(local_path))

    def delete_file(self, remote_path: str) -> None:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        self._sftp.remove(remote_path)

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        with self._sftp.open(remote_path, "rb") as file:
            file.seek(offset)
            data = file.read(size)

        if isinstance(data, str):
            return data.encode("utf-8")

        return data

    def close(self):
        if self._sftp:
            self._sftp.close()
        if self._ssh:
            self._ssh.close()
