import json
from pathlib import Path

from diode_metrics_exporter.sink.sink import MetadataSink


class JsonlMetadataFileSink(MetadataSink):
    def __init__(self, output_file: Path) -> None:
        self._output_file = output_file
        self._output_file.parent.mkdir(parents=True, exist_ok=True)

    def write(self, metadata: dict[str, str]) -> None:
        with self._output_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(metadata) + "\n")
