from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def build_report(path: Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        raise ValueError("CSV is empty")

    headers = [header.strip() for header in rows[0]]
    if not headers or any(not header for header in headers):
        raise ValueError("CSV header contains an empty column")

    normalized: list[dict[str, str]] = []
    blank_rows = 0
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            blank_rows += 1
            continue
        padded = row + [""] * (len(headers) - len(row))
        normalized.append({
            header: padded[index].strip()
            for index, header in enumerate(headers)
        })

    row_keys = [tuple(row[header] for header in headers) for row in normalized]
    counts = Counter(row_keys)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    empty_cells = sum(
        1 for row in normalized for header in headers if not row[header]
    )

    return {
        "file": str(path),
        "columns": headers,
        "rows": len(normalized),
        "blank_rows": blank_rows,
        "duplicate_rows": duplicates,
        "empty_cells": empty_cells,
    }
