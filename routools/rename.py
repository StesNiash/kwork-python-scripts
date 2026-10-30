from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenamePlan:
    source: Path
    target: Path


def build_plan(root: Path, pattern: str) -> list[RenamePlan]:
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    files = sorted(
        (path for path in root.iterdir() if path.is_file() and not path.is_symlink()),
        key=lambda path: path.name.lower(),
    )
    plans: list[RenamePlan] = []
    for index, source in enumerate(files, start=1):
        new_name = pattern.format(
            n=index,
            name=source.stem,
            ext=source.suffix.lstrip("."),
            suffix=source.suffix,
        )
        if not new_name or new_name in {".", ".."} or "/" in new_name or "\\" in new_name:
            raise ValueError(f"invalid target name: {new_name!r}")
        plans.append(RenamePlan(source, source.with_name(new_name)))

    targets = [plan.target for plan in plans]
    if len(set(targets)) != len(targets):
        raise ValueError("pattern produces duplicate names")

    source_set = {plan.source.resolve() for plan in plans}
    for target in targets:
        if target.exists() and target.resolve() not in source_set:
            raise FileExistsError(f"target already exists: {target}")

    return plans


def apply_plan(plans: list[RenamePlan]) -> list[RenamePlan]:
    temporary: list[tuple[Path, Path]] = []
    for index, plan in enumerate(plans):
        temp = plan.source.with_name(f".routools-tmp-{index}-{plan.source.name}")
        plan.source.rename(temp)
        temporary.append((temp, plan.target))
    for temp, target in temporary:
        shutil.move(str(temp), str(target))
    return plans


def report(plans: list[RenamePlan]) -> dict:
    return {
        "files": len(plans),
        "items": [
            {"source": str(plan.source), "target": str(plan.target)}
            for plan in plans
        ],
    }
