import logging
import time

from diode_metrics_exporter.processor.processor import (
    FileProcessorRouter,
    PeriodicProcessor,
)
from diode_metrics_exporter.processor.utils import build_remote_path

from .config import SFTPConfig
from .sftp_client import SFTPClient
from .storage import LocalFileStore

logger = logging.getLogger(__name__)


class SFTPWatcher:
    def __init__(
        self,
        config: SFTPConfig,
        sftp_client: SFTPClient,
        router: FileProcessorRouter,
        store: LocalFileStore,
    ) -> None:
        self._config = config
        self._sftp_client = sftp_client
        self._store = store
        self._router = router
        self._running = False

    def run_forever(self) -> None:
        self._running = True

        while self._running:
            try:
                self.run_once()
            except Exception:
                logger.exception("Error during SFTP polling loop")

            time.sleep(self._config.poll_interval_seconds)

    def run_once(self) -> None:
        files = self._sftp_client.list_files(self._config.remote_dir)

        if not files:
            logger.info("No files found in remote directory")

        for remote_file in files:
            remote_path = build_remote_path(self._config, remote_file)

            processor = self._router.find_processor(remote_file, remote_path)

            if processor is None:
                logger.info(
                    "No processor found for file: %s",
                    remote_file.name,
                )
                continue

            try:
                processor.process(
                    file=remote_file,
                    remote_path=remote_path,
                    sftp_client=self._sftp_client,
                    store=self._store,
                )
            except Exception:
                logger.exception(
                    "Failed processing file: %s",
                    remote_file.name,
                )

        # lifecycle hook
        self._run_periodic_hooks()

    def _run_periodic_hooks(self) -> None:
        for processor in self._router.processors:
            if isinstance(processor, PeriodicProcessor):
                try:
                    processor.on_poll_complete()
                except Exception:
                    logger.exception(
                        "Error in periodic processor: %s",
                        type(processor).__name__,
                    )

    def stop(self) -> None:
        self._running = False
