import logging
from pathlib import Path

from diode_metrics_exporter.config import SFTPConfig
from diode_metrics_exporter.processor.healthcheck_processor import (
    HealthcheckMonitor,
    HealthcheckProcessor,
)
from diode_metrics_exporter.processor.ignore_processor import IgnoreProcessor
from diode_metrics_exporter.processor.processor import FileProcessorRouter
from diode_metrics_exporter.processor.tarball_processor import TarballProcessor
from diode_metrics_exporter.sftp_client import ParamikoSFTPClient
from diode_metrics_exporter.sftp_watcher import SFTPWatcher
from diode_metrics_exporter.sink.jsonl_sink import JsonlMetadataFileSink
from diode_metrics_exporter.sink.sink import CompositeMetadataSink
from diode_metrics_exporter.storage import LocalFileStore


def run_app(env_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    config = SFTPConfig.from_env(env_file)

    sftp_client = ParamikoSFTPClient(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
    )

    store = LocalFileStore(config.local_dir)

    healthcheck_monitor = HealthcheckMonitor(
        record_file=config.local_dir / "HEALTHCHECK_RECORD",
        state_file=config.local_dir / ".healthcheck_state.json",
        timeout_seconds=60,
    )

    metadata_sink = CompositeMetadataSink(
        sinks=[
            JsonlMetadataFileSink(config.local_dir / "TARBALL_METADATA_RECORD.jsonl"),
            # LokiMetadataSink(),  # TODO
        ]
    )

    router = FileProcessorRouter(
        processors=[
            HealthcheckProcessor(healthcheck_monitor),
            TarballProcessor(metadata_sink),
            IgnoreProcessor(),
        ]
    )

    sftp_client.connect()

    try:
        watcher = SFTPWatcher(
            config=config,
            sftp_client=sftp_client,
            store=store,
            router=router,
        )

        watcher.run_forever()

    finally:
        sftp_client.close()
