from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DuplicateGroup:
    digest: str
    keep: Path
    duplicates: tuple[Path, ...]


def file_digest(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(root: Path) -> list[DuplicateGroup]:
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and not path.is_symlink()),
        key=lambda path: str(path).lower(),
    )
    by_size: dict[int, list[Path]] = {}
    for path in files:
        by_size.setdefault(path.stat().st_size, []).append(path)

    groups: list[DuplicateGroup] = []
    for same_size in by_size.values():
        if len(same_size) < 2:
            continue
        by_digest: dict[str, list[Path]] = {}
        for path in same_size:
            by_digest.setdefault(file_digest(path), []).append(path)
        for digest, paths in by_digest.items():
            if len(paths) < 2:
                continue
            ordered = sorted(paths, key=lambda path: str(path).lower())
            groups.append(DuplicateGroup(digest, ordered[0], tuple(ordered[1:])))

    return sorted(groups, key=lambda group: str(group.keep).lower())


def unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def apply_quarantine(groups: list[DuplicateGroup], quarantine: Path) -> list[tuple[Path, Path]]:
    quarantine = Path(quarantine)
    quarantine.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    for group in groups:
        for duplicate in group.duplicates:
            target = unique_target(quarantine / duplicate.name)
            shutil.move(str(duplicate), str(target))
            moved.append((duplicate, target))
    return moved


def report(groups: list[DuplicateGroup]) -> dict:
    return {
        "groups": len(groups),
        "duplicates": sum(len(group.duplicates) for group in groups),
        "items": [
            {
                "keep": str(group.keep),
                "duplicates": [str(path) for path in group.duplicates],
                "sha256": group.digest,
            }
            for group in groups
        ],
    }
