import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class SFTPConfig:
    host: str
    port: int
    username: str
    password: str | None
    private_key_path: Path | None
    remote_dir: str
    local_dir: Path
    poll_interval_seconds: int = 10

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "SFTPConfig":
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        private_key = os.getenv("SFTP_PRIVATE_KEY_PATH")

        return cls(
            host=_required("SFTP_HOST"),
            port=int(os.getenv("SFTP_PORT", "22")),
            username=_required("SFTP_USERNAME"),
            password=os.getenv("SFTP_PASSWORD"),
            private_key_path=Path(private_key) if private_key else None,
            remote_dir=_required("SFTP_REMOTE_DIR"),
            local_dir=Path(_required("SFTP_LOCAL_DIR")),
            poll_interval_seconds=int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", 10)),
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
