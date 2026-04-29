from collections.abc import Mapping
from typing import Protocol


class MetadataSink(Protocol):
    def write(self, metadata: Mapping[str, object]) -> None: ...


class CompositeMetadataSink:
    def __init__(self, sinks: list[MetadataSink]) -> None:
        self._sinks = sinks

    def write(self, metadata: Mapping[str, object]) -> None:
        for sink in self._sinks:
            sink.write(metadata)
