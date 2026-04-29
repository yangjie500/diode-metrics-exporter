import logging

from diode_metrics_exporter.sftp_client import RemoteFile, SFTPClient
from diode_metrics_exporter.storage import LocalFileStore

logger = logging.getLogger(__name__)


class IgnoreProcessor:
    def can_process(self, file: RemoteFile, remote_path: str) -> bool:
        return True

    def process(
        self,
        file: RemoteFile,
        remote_path: str,
        sftp_client: SFTPClient,
        store: LocalFileStore,
    ) -> None:
        logger.info("Ignoring unsupported file: %s", file.name)
