import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from diode_metrics_exporter.processor.healthcheck_processor import (
    HealthcheckMonitor,
    HealthcheckProcessor,
)
from diode_metrics_exporter.sftp_client import RemoteFile
from diode_metrics_exporter.storage import LocalFileStore

##### HealthcheckMonitor #####


def make_monitor(tmp_path: Path, timeout_seconds: int = 3600) -> HealthcheckMonitor:
    return HealthcheckMonitor(
        record_file=tmp_path / "HEALTHCHECK_RECORD",
        state_file=tmp_path / ".healthcheck_state.json",
        timeout_seconds=timeout_seconds,
    )


def test_record_seen_writes_record_and_state(tmp_path: Path) -> None:
    monitor = make_monitor(tmp_path)

    monitor.record_seen()

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")
    state = json.loads(
        (tmp_path / ".healthcheck_state.json").read_text(encoding="utf-8")
    )

    assert "HEALTHCHECK received" in record
    assert state["last_seen"] is not None
    assert state["alert_active"] is False


def test_timeout_writes_alert_and_updates_state(tmp_path: Path) -> None:
    monitor = make_monitor(tmp_path)

    monitor._last_seen = datetime.now(UTC) - timedelta(minutes=61)  # pyright: ignore[reportPrivateUsage]
    monitor.check_timeout()

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")
    state = json.loads(
        (tmp_path / ".healthcheck_state.json").read_text(encoding="utf-8")
    )

    assert (
        "Have not seen any HEALTHCHECK File for more than 61. Is it Working?" in record
    )
    assert state["alert_active"] is True


def test_timeout_alert_is_written_only_once(tmp_path: Path) -> None:
    monitor = make_monitor(tmp_path)

    monitor._last_seen = datetime.now(UTC) - timedelta(minutes=61)  # pyright: ignore[reportPrivateUsage]

    monitor.check_timeout()
    monitor.check_timeout()

    lines = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8").splitlines()

    alert_lines = [
        line for line in lines if "Have not seen any HEALTHCHECK File" in line
    ]

    assert len(alert_lines) == 1


def test_record_seen_restores_active_alert(tmp_path: Path) -> None:
    monitor = make_monitor(tmp_path)

    monitor._last_seen = datetime.now(UTC) - timedelta(minutes=61)  # pyright: ignore[reportPrivateUsage]
    monitor.check_timeout()

    monitor.record_seen()

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")
    state = json.loads(
        (tmp_path / ".healthcheck_state.json").read_text(encoding="utf-8")
    )

    assert "HEALTHCHECK restored" in record
    assert "HEALTHCHECK received" in record
    assert state["alert_active"] is False


def test_state_is_restored_after_restart(tmp_path: Path) -> None:
    first_monitor = make_monitor(tmp_path)
    old_time = datetime.now(UTC) - timedelta(minutes=61)

    first_monitor._last_seen = old_time  # pyright: ignore[reportPrivateUsage]
    first_monitor._save_state()  # pyright: ignore[reportPrivateUsage]

    restarted_monitor = make_monitor(tmp_path)

    restarted_monitor.check_timeout()

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")

    assert "Have not seen any HEALTHCHECK File" in record


def test_no_timeout_before_first_healthcheck(tmp_path: Path) -> None:
    monitor = make_monitor(tmp_path)

    monitor.check_timeout()

    assert not (tmp_path / "HEALTHCHECK_RECORD").exists()
    assert not (tmp_path / ".healthcheck_state.json").exists()


##### HealthcheckProcessor #####


class FakeSFTPClient:
    def __init__(self) -> None:
        self.deleted_files: list[str] = []

    def delete_file(self, remote_path: str) -> None:
        self.deleted_files.append(remote_path)


def test_healthcheck_processor_can_process_healthcheck_file(
    tmp_path: Path,
) -> None:
    monitor = HealthcheckMonitor(
        record_file=tmp_path / "HEALTHCHECK_RECORD",
        state_file=tmp_path / ".healthcheck_state.json",
        timeout_seconds=3600,
    )

    processor = HealthcheckProcessor(monitor)

    assert (
        processor.can_process(
            RemoteFile(name="HEALTHCHECK", mtime=100, size=1),
            "/incoming/HEALTHCHECK",
        )
        is True
    )

    assert (
        processor.can_process(
            RemoteFile(name="report.tar.gz", mtime=100, size=1),
            "/incoming/report.tar.gz",
        )
        is False
    )


def test_healthcheck_processor_records_seen_and_deletes_remote_file(
    tmp_path: Path,
) -> None:
    monitor = HealthcheckMonitor(
        record_file=tmp_path / "HEALTHCHECK_RECORD",
        state_file=tmp_path / ".healthcheck_state.json",
        timeout_seconds=3600,
    )

    processor = HealthcheckProcessor(monitor)
    sftp_client = FakeSFTPClient()
    store = LocalFileStore(tmp_path / "downloads")

    file = RemoteFile(name="HEALTHCHECK", mtime=100, size=1)

    processor.process(
        file=file,
        remote_path="/incoming/HEALTHCHECK",
        sftp_client=sftp_client,  # type: ignore[arg-type]
        store=store,
    )

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")

    assert "HEALTHCHECK received" in record
    assert sftp_client.deleted_files == ["/incoming/HEALTHCHECK"]


def test_healthcheck_processor_on_poll_complete_checks_timeout(
    tmp_path: Path,
) -> None:
    monitor = HealthcheckMonitor(
        record_file=tmp_path / "HEALTHCHECK_RECORD",
        state_file=tmp_path / ".healthcheck_state.json",
        timeout_seconds=3600,
    )

    processor = HealthcheckProcessor(monitor)

    monitor._last_seen = datetime.now(UTC) - timedelta(minutes=61)  # pyright: ignore[reportPrivateUsage]

    processor.on_poll_complete()

    record = (tmp_path / "HEALTHCHECK_RECORD").read_text(encoding="utf-8")

    assert "Have not seen any HEALTHCHECK File" in record
