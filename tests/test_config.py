from pathlib import Path

from diode_metrics_exporter.config import SFTPConfig


def test_sftp_config_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SFTP_HOST=sftp.example.com",
                "SFTP_PORT=2222",
                "SFTP_USERNAME=myuser",
                "SFTP_PASSWORD=mypassword",
                "SFTP_PRIVATE_KEY_PATH=/tmp/id_ed25519",
                "SFTP_REMOTE_DIR=/folder",
                f"SFTP_LOCAL_DIR={tmp_path / 'downloads'}",
                "SFTP_POLL_INTERVAL_SECONDS=5",
            ]
        )
    )

    config = SFTPConfig.from_env(env_file)

    assert config.host == "sftp.example.com"
    assert config.port == 2222
    assert config.username == "myuser"
    assert config.password == "mypassword"
    assert config.private_key_path == Path("/tmp/id_ed25519")
    assert config.remote_dir == "/folder"
    assert config.local_dir == tmp_path / "downloads"
    assert config.poll_interval_seconds == 5
