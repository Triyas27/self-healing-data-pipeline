import csv
import io
from pathlib import Path
from typing import IO, Union

CsvSource = Union[str, Path, IO[str], IO[bytes], list[dict[str, str]]]


def _normalize_column_name(name: str) -> str:
    return name.strip().lower()


def _normalize_value(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def _normalize_row(row: dict[str, str | None]) -> dict[str, str | None]:
    return {
        _normalize_column_name(key): _normalize_value(value)
        for key, value in row.items()
        if key is not None
    }


def read_csv_rows(source: CsvSource) -> list[dict[str, str]]:
    """Accepts a batch from a file path, an uploaded file-like object, or an
    already-generated list of rows (e.g. the synthetic generator's output).
    Normalizes column names and strips whitespace from values before validation.
    """
    if isinstance(source, list):
        raw_rows = source
    elif isinstance(source, (str, Path)):
        with open(source, newline="", encoding="utf-8") as f:
            raw_rows = list(csv.DictReader(f))
    else:
        content = source.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        raw_rows = list(csv.DictReader(io.StringIO(content)))

    return [_normalize_row(row) for row in raw_rows]
