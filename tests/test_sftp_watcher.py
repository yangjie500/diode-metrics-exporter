# from pathlib import Path

# from diode_metrics_exporter.config import SFTPConfig
# from diode_metrics_exporter.sftp_client import RemoteFile
# from diode_metrics_exporter.sftp_watcher import SFTPWatcher
# from diode_metrics_exporter.storage import LocalFileStore


# class FakeSFTPClient:
#     def __init__(self, files: list[RemoteFile]) -> None:
#         self.files = files
#         self.downloads: list[tuple[str, Path]] = []

#     def list_files(self, remote_dir: str) -> list[RemoteFile]:
#         return self.files

#     def download_file(self, remote_path: str, local_path: Path) -> None:
#         self.downloads.append((remote_path, local_path))

#     def close(self) -> None:
#         pass


# def make_config(tmp_path: Path) -> SFTPConfig:
#     return SFTPConfig(
#         host="localhost",
#         port=22,
#         username="user",
#         password="pass",
#         private_key_path=None,
#         remote_dir="/incoming",
#         local_dir=tmp_path / "downloads",
#         poll_interval_seconds=1,
#     )


# def test_run_once_downloads_all_new_files(tmp_path: Path) -> None:
#     config = make_config(tmp_path)
#     store = LocalFileStore(config.local_dir)

#     client = FakeSFTPClient(
#         [
#             RemoteFile(name="a.tar.gz", mtime=100, size=10),
#             RemoteFile(name="b.tar.gz", mtime=200, size=20),
#         ]
#     )

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == [
#         (
#             "/incoming/a.tar.gz",
#             tmp_path / "downloads" / "a.tar.gz",
#         ),
#         (
#             "/incoming/b.tar.gz",
#             tmp_path / "downloads" / "b.tar.gz",
#         ),
#     ]

#     assert (
#         store.already_downloaded(RemoteFile(name="a.tar.gz", mtime=100, size=10))
#         is True
#     )

#     assert (
#         store.already_downloaded(RemoteFile(name="b.tar.gz", mtime=200, size=20))
#         is True
#     )


# def test_run_once_skips_already_downloaded_identity(
#     tmp_path: Path,
# ) -> None:
#     config = make_config(tmp_path)
#     store = LocalFileStore(config.local_dir)

#     existing = RemoteFile(
#         name="a.tar.gz",
#         mtime=100,
#         size=10,
#     )

#     store.mark_downloaded(existing)

#     client = FakeSFTPClient(
#         [
#             existing,
#             RemoteFile(
#                 name="b.tar.gz",
#                 mtime=200,
#                 size=20,
#             ),
#         ]
#     )

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == [
#         (
#             "/incoming/b.tar.gz",
#             tmp_path / "downloads" / "b.tar.gz",
#         )
#     ]


# def test_run_once_same_filename_redownloads_when_changed(
#     tmp_path: Path,
# ) -> None:
#     config = make_config(tmp_path)
#     store = LocalFileStore(config.local_dir)

#     old_file = RemoteFile(
#         name="report.tar.gz",
#         mtime=100,
#         size=10,
#     )

#     new_file = RemoteFile(
#         name="report.tar.gz",
#         mtime=200,
#         size=99,
#     )

#     store.mark_downloaded(old_file)

#     client = FakeSFTPClient([new_file])

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == [
#         (
#             "/incoming/report.tar.gz",
#             tmp_path / "downloads" / "report.tar.gz",
#         )
#     ]

#     assert store.already_downloaded(new_file) is True


# def test_run_once_does_nothing_when_no_files(
#     tmp_path: Path,
# ) -> None:
#     config = make_config(tmp_path)
#     store = LocalFileStore(config.local_dir)

#     client = FakeSFTPClient([])

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == []


# def test_run_once_does_nothing_when_all_files_downloaded(
#     tmp_path: Path,
# ) -> None:
#     config = make_config(tmp_path)
#     store = LocalFileStore(config.local_dir)

#     file_a = RemoteFile(
#         name="a.tar.gz",
#         mtime=100,
#         size=10,
#     )

#     file_b = RemoteFile(
#         name="b.tar.gz",
#         mtime=200,
#         size=20,
#     )

#     store.mark_downloaded(file_a)
#     store.mark_downloaded(file_b)

#     client = FakeSFTPClient([file_a, file_b])

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == []


# def test_run_once_uses_posix_remote_paths_and_native_local_paths(
#     tmp_path: Path,
# ) -> None:
#     config = SFTPConfig(
#         host="localhost",
#         port=22,
#         username="user",
#         password="pass",
#         private_key_path=None,
#         remote_dir="/incoming/reports",
#         local_dir=tmp_path / "downloads",
#         poll_interval_seconds=1,
#     )

#     store = LocalFileStore(config.local_dir)

#     remote_file = RemoteFile(
#         name="report.tar.gz",
#         mtime=100,
#         size=10,
#     )

#     client = FakeSFTPClient([remote_file])

#     watcher = SFTPWatcher(config, client, store)

#     watcher.run_once()

#     assert client.downloads == [
#         (
#             "/incoming/reports/report.tar.gz",
#             tmp_path / "downloads" / "report.tar.gz",
#         )
#     ]
