import json
import logging
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from diode_metrics_exporter.sftp_client import RemoteFile, SFTPClient
from diode_metrics_exporter.sink.sink import MetadataSink
from diode_metrics_exporter.storage import LocalFileStore

logger = logging.getLogger(__name__)


class TarballProcessor:
    GZIP_MAGIC = b"\x1f\x8b"
    TAR_MAGIC_OFFSET = 257
    TAR_MAGIC = b"ustar"

    def __init__(self, metadata_sink: MetadataSink) -> None:
        self._metadata_sink = metadata_sink

    def can_process(self, file: RemoteFile, remote_path: str) -> bool:
        # Placeholder first. Replace later with magic header detection.
        return file.name.endswith((".tar", ".tar.gz", ".tgz", ".bundle"))

    def process(
        self,
        file: RemoteFile,
        remote_path: str,
        sftp_client: SFTPClient,
        store: LocalFileStore,
    ) -> None:
        if store.already_downloaded(file):
            logger.info("Skipping already downloaded tarball: %s", file.name)
            return

        if not self._is_tarball(remote_path, sftp_client):
            logger.info("File is not a valid tarball: %s", file.name)
            return

        local_path = store.destination_for(file.name)

        logger.info("Downloading tarball: %s -> %s", remote_path, local_path)
        sftp_client.download_file(remote_path, local_path)

        self._extract_and_validate_metadata(local_path)

        store.mark_downloaded(file)

    def _is_tarball(self, remote_path: str, sftp_client: SFTPClient) -> bool:
        first_two_bytes = sftp_client.read_bytes(remote_path, size=2)

        if first_two_bytes == TarballProcessor.GZIP_MAGIC:
            return True

        tar_magic = sftp_client.read_bytes(
            remote_path,
            size=len(TarballProcessor.TAR_MAGIC),
            offset=TarballProcessor.TAR_MAGIC_OFFSET,
        )

        return tar_magic == TarballProcessor.TAR_MAGIC

    def _extract_and_validate_metadata(self, tarball_path: Path) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = Path(temp_dir)

            logger.info("Extracting tarball to temporary directory: %s", extract_dir)

            self._safe_extract_tarball(tarball_path, extract_dir)

            metadata_file = extract_dir / "METADATA.json"

            if not metadata_file.exists():
                raise FileNotFoundError(
                    f"Tarball {tarball_path.name} does not contain METADATA.json"
                )

            logger.info("Found METADATA.json in tarball: %s", tarball_path.name)

            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            required_keys = {"SIZEOFFILE", "TIMESTAMP"}
            missing_keys = required_keys - metadata.keys()

            if missing_keys:
                raise ValueError(
                    f"METADATA.json missing required keys: {sorted(missing_keys)}"
                )

            # --- Parse SIZEOFFILE ---
            # Expect format: "12323 KB"
            size_str = str(metadata["SIZEOFFILE"])
            size_value_str, size_unit = size_str.split()

            size_kb = float(size_value_str)

            if size_unit.upper() != "KB":
                raise ValueError(f"Unsupported SIZEOFFILE unit: {size_unit}")

            size_mb = size_kb / 1024
            size_gb = size_mb / 1024

            # --- Parse TIMESTAMP ---
            # Format: 20241028T115959
            ts_str = str(metadata["TIMESTAMP"])

            try:
                ts = datetime.strptime(ts_str, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
            except ValueError as err:
                raise ValueError(f"Invalid TIMESTAMP format: {ts_str}") from err

            now = datetime.now(UTC)
            time_taken_seconds = (now - ts).total_seconds()

            record = {
                "tarball_name": tarball_path.name,
                "SIZEOFFILE": size_str,
                "TIMESTAMP": ts_str,
                "TIME_TAKEN_SECONDS": int(time_taken_seconds),
                "TIME_TAKEN_MINUTES": round(time_taken_seconds / 60, 2),
                "TIME_TAKEN_HOURS": round(time_taken_seconds / 3600, 2),
                "SIZE_KB": round(size_kb, 2),
                "SIZE_MB": round(size_mb, 2),
                "SIZE_GB": round(size_gb, 4),
            }

            self._metadata_sink.write(record)

            logger.info("Recorded METADATA.json for tarball: %s", tarball_path.name)

    def _safe_extract_tarball(self, tarball_path: Path, extract_dir: Path) -> None:
        with tarfile.open(tarball_path, mode="r:*") as tar:
            for member in tar.getmembers():
                target_path = extract_dir / member.name

                if not self._is_safe_path(extract_dir, target_path):
                    raise ValueError(f"Unsafe path detected in tarball: {member.name}")

            tar.extractall(extract_dir, filter="data")

    def _is_safe_path(self, base_dir: Path, target_path: Path) -> bool:
        base_dir = base_dir.resolve()
        target_path = target_path.resolve()

        return base_dir == target_path or base_dir in target_path.parents
