import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from diode_metrics_exporter.processor.processor import FileProcessor, PeriodicProcessor
from diode_metrics_exporter.sftp_client import RemoteFile, SFTPClient
from diode_metrics_exporter.storage import LocalFileStore

logger = logging.getLogger(__name__)


class HealthcheckMonitor:
    def __init__(
        self,
        record_file: Path,
        state_file: Path,
        timeout_seconds: int,
    ) -> None:
        self._record_file = record_file
        self._state_file = state_file
        self._timeout = timedelta(seconds=timeout_seconds)

        self._record_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        state = self._load_state()

        self._last_seen = state["last_seen"]
        self._alert_active = state["alert_active"]

    def record_seen(self) -> None:
        now = datetime.now(UTC)

        if self._alert_active:
            self._append_record(f"{now.isoformat()} HEALTHCHECK restored")

        self._append_record(f"{now.isoformat()} HEALTHCHECK received")

        self._last_seen = now
        self._alert_active = False
        self._save_state()

    def check_timeout(self) -> None:
        if self._last_seen is None:
            return

        now = datetime.now(UTC)
        elapsed = now - self._last_seen

        if elapsed >= self._timeout:
            self.on_timeout(elapsed)

    def on_timeout(self, elapsed: timedelta) -> None:
        if self._alert_active:
            return

        minutes = int(elapsed.total_seconds() // 60)

        self._append_record(
            "Have not seen any HEALTHCHECK File "
            f"for more than {minutes}. "
            "Is it Working?"
        )

        self._alert_active = True
        self._save_state()

    def _append_record(self, text: str) -> None:
        with self._record_file.open("a", encoding="utf-8") as file:
            file.write(text + "\n")

    def _load_state(self) -> dict[str, Any]:
        if not self._state_file.exists():
            return {
                "last_seen": None,
                "alert_active": False,
            }

        raw = json.loads(self._state_file.read_text(encoding="utf-8"))

        last_seen_raw = raw.get("last_seen")

        return {
            "last_seen": (
                datetime.fromisoformat(last_seen_raw) if last_seen_raw else None
            ),
            "alert_active": bool(raw.get("alert_active", False)),
        }

    def _save_state(self) -> None:
        payload = {
            "last_seen": (self._last_seen.isoformat() if self._last_seen else None),
            "alert_active": self._alert_active,
        }

        self._state_file.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


class HealthcheckProcessor(FileProcessor, PeriodicProcessor):
    def __init__(self, monitor: HealthcheckMonitor) -> None:
        self._monitor = monitor

    def can_process(self, file: RemoteFile, remote_path: str) -> bool:
        return file.name == "HEALTHCHECK"

    def process(
        self,
        file: RemoteFile,
        remote_path: str,
        sftp_client: SFTPClient,
        store: LocalFileStore,
    ) -> None:
        logger.info("HEALTHCHECK received: %s", remote_path)

        self._monitor.record_seen()
        sftp_client.delete_file(remote_path)

        logger.info("HEALTHCHECK deleted: %s", remote_path)

    def on_poll_complete(self) -> None:
        self._monitor.check_timeout()
