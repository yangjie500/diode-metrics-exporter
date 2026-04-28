from pathlib import PurePosixPath

from diode_metrics_exporter.config import SFTPConfig
from diode_metrics_exporter.sftp_client import RemoteFile


def build_remote_path(config: SFTPConfig, file: RemoteFile) -> str:
    return str(PurePosixPath(config.remote_dir) / file.name)
