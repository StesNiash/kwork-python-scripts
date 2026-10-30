from __future__ import annotations

import argparse
import json
from pathlib import Path

from .csv_report import build_report as csv_report
from .dedupe import apply_quarantine, find_duplicates, report as dedupe_report
from .rename import apply_plan, build_plan, report as rename_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="routools",
        description="Небольшие CLI-утилиты для файлов, CSV и рутины.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dedupe = subparsers.add_parser("dedupe", help="найти одинаковые файлы")
    dedupe.add_argument("path", type=Path)
    dedupe.add_argument("--apply", action="store_true", help="переместить дубли в quarantine")
    dedupe.add_argument("--quarantine", type=Path, default=Path("quarantine"))
    dedupe.add_argument("--json", action="store_true")

    rename = subparsers.add_parser("rename", help="пакетно переименовать файлы")
    rename.add_argument("path", type=Path)
    rename.add_argument("--pattern", default="file_{n:03d}{suffix}")
    rename.add_argument("--apply", action="store_true")
    rename.add_argument("--json", action="store_true")

    csv_parser = subparsers.add_parser("csv-report", help="проверить CSV")
    csv_parser.add_argument("path", type=Path)
    csv_parser.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "dedupe":
            groups = find_duplicates(args.path)
            data = dedupe_report(groups)
            if args.apply:
                moved = apply_quarantine(groups, args.quarantine)
                data["moved"] = len(moved)
            print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else _dedupe_text(data))
            return 0

        if args.command == "rename":
            plans = build_plan(args.path, args.pattern)
            if args.apply:
                apply_plan(plans)
            data = rename_report(plans)
            data["applied"] = bool(args.apply)
            print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else _rename_text(data))
            return 0

        if args.command == "csv-report":
            data = csv_report(args.path)
            print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else _csv_text(data))
            return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")

    return 2


def _dedupe_text(data: dict) -> str:
    lines = [f"groups: {data['groups']}", f"duplicates: {data['duplicates']}"]
    for item in data["items"]:
        lines.append(f"keep: {item['keep']}")
        lines.extend(f"  duplicate: {path}" for path in item["duplicates"])
    if "moved" in data:
        lines.append(f"moved: {data['moved']}")
    return "\n".join(lines)


def _rename_text(data: dict) -> str:
    lines = [f"files: {data['files']}", f"applied: {data['applied']}"]
    for item in data["items"]:
        lines.append(f"{item['source']} -> {item['target']}")
    return "\n".join(lines)


def _csv_text(data: dict) -> str:
    return "\n".join([
        f"columns: {', '.join(data['columns'])}",
        f"rows: {data['rows']}",
        f"blank_rows: {data['blank_rows']}",
        f"duplicate_rows: {data['duplicate_rows']}",
        f"empty_cells: {data['empty_cells']}",
    ])
