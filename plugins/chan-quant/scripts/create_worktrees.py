"""Create independent plugin task worktrees from a clean Git base checkout."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, capture_output=True)
    return result.stdout.strip()


def ref_exists(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "show-ref", "--verify", ref],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    if not value:
        raise ValueError("task names must contain letters or digits")
    return value


def create(repo: Path, base: str, root: Path, tasks: list[str], dry_run: bool) -> list[tuple[str, Path, str]]:
    if git(repo, "status", "--short"):
        raise RuntimeError("base checkout is dirty; preserve existing changes before creating task worktrees")
    if not ref_exists(repo, f"refs/heads/{base}"):
        raise RuntimeError(f"base branch does not exist locally: {base}")
    root = root.resolve()
    results = []
    seen: set[str] = set()
    for raw in tasks:
        task = slugify(raw)
        if task in seen:
            raise ValueError(f"duplicate task: {task}")
        seen.add(task)
        branch = f"codex/plugin/{task}"
        path = root / task
        if path.exists():
            raise RuntimeError(f"worktree path already exists: {path}")
        if ref_exists(repo, f"refs/heads/{branch}"):
            raise RuntimeError(f"task branch already exists: {branch}")
        results.append((branch, path, task))
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
        for branch, path, _ in results:
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", branch, str(path), base], check=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", default="main")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--task", action="append", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    results = create(args.repo.resolve(), args.base, args.root, args.task, args.dry_run)
    for branch, path, task in results:
        print(f"{task}\t{branch}\t{path}")


if __name__ == "__main__":
    main()
