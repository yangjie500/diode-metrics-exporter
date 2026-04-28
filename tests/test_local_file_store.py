from pathlib import Path

from diode_metrics_exporter.sftp_client import RemoteFile
from diode_metrics_exporter.storage import LocalFileStore


def test_init_creates_local_directory(tmp_path: Path) -> None:
    local_dir = tmp_path / "downloads"

    assert not local_dir.exists()

    LocalFileStore(local_dir)

    assert local_dir.exists()
    assert local_dir.is_dir()


def test_destination_for_returns_expected_path(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    result = store.destination_for("report.tar.gz")

    assert result == tmp_path / "downloads" / "report.tar.gz"


def test_identity_for_uses_name_size_and_mtime(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    remote_file = RemoteFile(
        name="report.tar.gz",
        size=12345,
        mtime=2704261232,
    )

    assert store.identity_for(remote_file) == "report.tar.gz|12345|2704261232"


def test_downloaded_identities_empty_when_state_file_missing(
    tmp_path: Path,
) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    assert store.downloaded_identities() == set()


def test_mark_downloaded_adds_identity(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    remote_file = RemoteFile(
        name="report.tar.gz",
        size=100,
        mtime=200,
    )

    store.mark_downloaded(remote_file)

    assert store.downloaded_identities() == {"report.tar.gz|100|200"}


def test_already_downloaded_returns_true_when_same_identity_exists(
    tmp_path: Path,
) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    remote_file = RemoteFile(
        name="report.tar.gz",
        size=100,
        mtime=200,
    )

    store.mark_downloaded(remote_file)

    assert store.already_downloaded(remote_file) is True


def test_already_downloaded_returns_false_when_same_name_but_changed(
    tmp_path: Path,
) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    old_file = RemoteFile(
        name="report.tar.gz",
        size=100,
        mtime=200,
    )

    new_file = RemoteFile(
        name="report.tar.gz",
        size=150,
        mtime=300,
    )

    store.mark_downloaded(old_file)

    assert store.already_downloaded(new_file) is False


def test_mark_downloaded_does_not_duplicate_entries(
    tmp_path: Path,
) -> None:
    store = LocalFileStore(tmp_path / "downloads")

    remote_file = RemoteFile(
        name="report.tar.gz",
        size=100,
        mtime=200,
    )

    store.mark_downloaded(remote_file)
    store.mark_downloaded(remote_file)

    state_file = tmp_path / "downloads" / ".downloaded"

    lines = state_file.read_text(encoding="utf-8").splitlines()

    assert lines == ["report.tar.gz|100|200"]


def test_downloaded_identities_ignores_blank_lines(
    tmp_path: Path,
) -> None:
    local_dir = tmp_path / "downloads"
    store = LocalFileStore(local_dir)

    state_file = local_dir / ".downloaded"
    state_file.write_text(
        ("a.tar.gz|10|100\n\nb.tar.gz|20|200\n   \n"),
        encoding="utf-8",
    )

    assert store.downloaded_identities() == {
        "a.tar.gz|10|100",
        "b.tar.gz|20|200",
    }
