from typing import Protocol


class MetadataSink(Protocol):
    def write(self, metadata: dict[str, str]) -> None: ...


class CompositeMetadataSink:
    def __init__(self, sinks: list[MetadataSink]) -> None:
        self._sinks = sinks

    def write(self, metadata: dict[str, str]) -> None:
        for sink in self._sinks:
            sink.write(metadata)
