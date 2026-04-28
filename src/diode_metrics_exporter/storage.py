from pathlib import Path

from .sftp_client import RemoteFile


class LocalFileStore:
    def __init__(self, local_dir: Path) -> None:
        self._local_dir = local_dir
        self._state_file = self._local_dir / ".downloaded"

        self._local_dir.mkdir(parents=True, exist_ok=True)

    def destination_for(self, filename: str) -> Path:
        return self._local_dir / filename

    def identity_for(self, file: RemoteFile) -> str:
        return f"{file.name}|{file.size}|{file.mtime}"

    def already_downloaded(self, file: RemoteFile) -> bool:
        return self.identity_for(file) in self.downloaded_identities()

    def mark_downloaded(self, file: RemoteFile) -> None:
        identity = self.identity_for(file)

        if identity in self.downloaded_identities():
            return

        with self._state_file.open("a", encoding="utf-8") as state_file:
            state_file.write(identity + "\n")

    def downloaded_identities(self) -> set[str]:
        if not self._state_file.exists():
            return set()

        content = self._state_file.read_text(encoding="utf-8")

        return {line.strip() for line in content.splitlines() if line.strip()}
