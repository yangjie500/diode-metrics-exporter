import tarfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from diode_metrics_exporter.processor.tarball_processor import TarballProcessor
from diode_metrics_exporter.sftp_client import RemoteFile
from diode_metrics_exporter.storage import LocalFileStore


class FakeSFTPClient:
    def __init__(self, header: bytes = b"", tar_magic: bytes = b"") -> None:
        self.header = header
        self.tar_magic = tar_magic
        self.downloads: list[tuple[str, Path]] = []

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes:
        if offset == 0:
            return self.header
        if offset == TarballProcessor.TAR_MAGIC_OFFSET:
            return self.tar_magic
        return b""

    def download_file(self, remote_path: str, local_path: Path) -> None:
        self.downloads.append((remote_path, local_path))


class FakeMetadataSink:
    def __init__(self) -> None:
        self.records: list[Mapping[str, object]] = []

    def write(self, metadata: Mapping[str, object]) -> None:
        self.records.append(metadata)


def make_processor(sink: FakeMetadataSink | None = None) -> TarballProcessor:
    return TarballProcessor(metadata_sink=sink or FakeMetadataSink())


def create_tarball(path: Path, include_metadata: bool = True) -> None:
    source_dir = path.parent / "source"
    source_dir.mkdir()

    if include_metadata:
        (source_dir / "METADATA.json").write_text(
            '{"SIZEOFFILE": "12323 KB", "TIMESTAMP": "20241028T115959"}',
            encoding="utf-8",
        )

    (source_dir / "data.txt").write_text("hello", encoding="utf-8")

    with tarfile.open(path, "w:gz") as tar:
        tar.add(source_dir, arcname=".")


def test_can_process_supported_suffixes() -> None:
    processor = make_processor()

    assert processor.can_process(RemoteFile("a.tar", 1, 1), "/incoming/a.tar")
    assert processor.can_process(RemoteFile("a.tar.gz", 1, 1), "/incoming/a.tar.gz")
    assert processor.can_process(RemoteFile("a.tgz", 1, 1), "/incoming/a.tgz")
    assert processor.can_process(RemoteFile("a.bundle", 1, 1), "/incoming/a.bundle")


def test_can_process_rejects_other_suffixes() -> None:
    processor = make_processor()

    assert not processor.can_process(RemoteFile("a.txt", 1, 1), "/incoming/a.txt")


def test_is_tarball_returns_true_for_gzip_magic() -> None:
    processor = make_processor()
    sftp = FakeSFTPClient(header=TarballProcessor.GZIP_MAGIC)

    assert processor._is_tarball("/incoming/a.tar.gz", sftp) is True  # pyright: ignore[reportArgumentType, reportPrivateUsage]


def test_is_tarball_returns_true_for_plain_tar_magic() -> None:
    processor = make_processor()
    sftp = FakeSFTPClient(header=b"xx", tar_magic=TarballProcessor.TAR_MAGIC)

    assert processor._is_tarball("/incoming/a.tar", sftp) is True  # pyright: ignore[reportArgumentType, reportPrivateUsage]


def test_is_tarball_returns_false_for_invalid_header() -> None:
    processor = make_processor()
    sftp = FakeSFTPClient(header=b"xx", tar_magic=b"xxxxx")

    assert processor._is_tarball("/incoming/a.txt", sftp) is False  # pyright: ignore[reportArgumentType, reportPrivateUsage]


def test_process_downloads_extracts_records_metadata_and_marks_downloaded(
    tmp_path: Path,
) -> None:
    tarball_path = tmp_path / "downloads" / "report.tar.gz"
    tarball_path.parent.mkdir()
    create_tarball(tarball_path, include_metadata=True)

    sink = FakeMetadataSink()
    processor = make_processor(sink)
    store = LocalFileStore(tmp_path / "downloads")
    sftp = FakeSFTPClient(header=TarballProcessor.GZIP_MAGIC)

    remote_file = RemoteFile(name="report.tar.gz", mtime=100, size=10)

    processor.process(
        file=remote_file,
        remote_path="/incoming/report.tar.gz",
        sftp_client=sftp,  # type: ignore[arg-type]
        store=store,
    )

    assert sftp.downloads == [
        (
            "/incoming/report.tar.gz",
            tmp_path / "downloads" / "report.tar.gz",
        )
    ]

    assert len(sink.records) == 1

    record = sink.records[0]

    assert record["tarball_name"] == "report.tar.gz"
    assert record["SIZEOFFILE"] == "12323 KB"
    assert record["TIMESTAMP"] == "20241028T115959"
    assert record["SIZE_KB"] == 12323.0
    assert record["SIZE_MB"] == round(12323 / 1024, 2)
    assert record["SIZE_GB"] == round(12323 / 1024 / 1024, 4)
    assert isinstance(record["TIME_TAKEN_SECONDS"], int)

    assert store.already_downloaded(remote_file) is True


def test_extract_raises_when_metadata_missing_required_keys(
    tmp_path: Path,
) -> None:
    tarball_path = tmp_path / "bad_metadata.tar.gz"

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "METADATA.json").write_text("{}", encoding="utf-8")

    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(source_dir, arcname=".")

    processor = make_processor()

    with pytest.raises(ValueError, match="METADATA.json missing required keys"):
        processor._extract_and_validate_metadata(tarball_path)  # pyright: ignore[reportPrivateUsage]


def test_process_skips_invalid_tarball(tmp_path: Path) -> None:
    processor = make_processor()
    store = LocalFileStore(tmp_path / "downloads")
    sftp = FakeSFTPClient(header=b"xx", tar_magic=b"xxxxx")

    remote_file = RemoteFile(name="bad.tar.gz", mtime=100, size=10)

    processor.process(
        file=remote_file,
        remote_path="/incoming/bad.tar.gz",
        sftp_client=sftp,  # type: ignore[arg-type]
        store=store,
    )

    assert sftp.downloads == []
    assert store.already_downloaded(remote_file) is False


def test_extract_raises_when_metadata_missing(tmp_path: Path) -> None:
    tarball_path = tmp_path / "missing_metadata.tar.gz"
    create_tarball(tarball_path, include_metadata=False)

    processor = make_processor()

    with pytest.raises(
        FileNotFoundError,
        match="does not contain METADATA.json",
    ):
        processor._extract_and_validate_metadata(tarball_path)  # pyright: ignore[reportPrivateUsage]


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    tarball_path = tmp_path / "evil.tar"

    evil_file = tmp_path / "evil.txt"
    evil_file.write_text("bad", encoding="utf-8")

    with tarfile.open(tarball_path, "w") as tar:
        tar.add(evil_file, arcname="../evil.txt")

    processor = make_processor()

    with pytest.raises(ValueError, match="Unsafe path detected"):
        processor._safe_extract_tarball(  # pyright: ignore[reportPrivateUsage]
            tarball_path,
            tmp_path / "extract",
        )


def test_process_skips_when_already_downloaded(tmp_path: Path) -> None:
    processor = make_processor()
    store = LocalFileStore(tmp_path / "downloads")
    sftp = FakeSFTPClient()

    remote_file = RemoteFile(
        name="report.tar.gz",
        mtime=100,
        size=10,
    )

    # Mark as already downloaded
    store.mark_downloaded(remote_file)

    processor.process(
        file=remote_file,
        remote_path="/incoming/report.tar.gz",
        sftp_client=sftp,  # type: ignore[arg-type]
        store=store,
    )

    # Should NOT download again
    assert sftp.downloads == []

    # Still marked as downloaded
    assert store.already_downloaded(remote_file) is True
