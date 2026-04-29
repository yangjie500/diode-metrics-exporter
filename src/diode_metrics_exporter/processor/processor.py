import logging
from typing import Protocol, runtime_checkable

from diode_metrics_exporter.sftp_client import RemoteFile, SFTPClient
from diode_metrics_exporter.storage import LocalFileStore

logger = logging.getLogger(__name__)


class FileProcessor(Protocol):
    def can_process(self, file: RemoteFile, remote_path: str) -> bool: ...

    def process(
        self,
        file: RemoteFile,
        remote_path: str,
        sftp_client: SFTPClient,
        store: LocalFileStore,
    ) -> None: ...


@runtime_checkable
class PeriodicProcessor(Protocol):
    def on_poll_complete(self) -> None: ...


class FileProcessorRouter:
    def __init__(self, processors: list[FileProcessor]) -> None:
        self.processors = processors

    def find_processor(
        self,
        file: RemoteFile,
        remote_path: str,
    ) -> FileProcessor | None:
        for processor in self.processors:
            if processor.can_process(file, remote_path):
                return processor

        return None

    def on_poll_complete(self) -> None:
        for processor in self.processors:
            if isinstance(processor, PeriodicProcessor):
                processor.on_poll_complete()
