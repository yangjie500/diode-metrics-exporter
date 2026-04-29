"""Interface for ``python -m diode_metrics_exporter``."""

from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .cli import run_app


def main(args: Sequence[str] | None = None) -> None:
    parser = ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
    )

    parsed = parser.parse_args(args)

    run_app(parsed.env_file)


if __name__ == "__main__":
    main()
