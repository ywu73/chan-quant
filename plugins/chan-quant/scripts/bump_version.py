"""Bump a Chan Quant plugin capability version and record the feature summary."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def read_base_version(plugin_root: Path) -> str:
    manifest = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    manifest_version = str(manifest.get("version", ""))
    version_file = (plugin_root / "VERSION").read_text(encoding="utf-8").strip()
    manifest_base = manifest_version.split("+", 1)[0]
    if not SEMVER.fullmatch(manifest_base) or not SEMVER.fullmatch(version_file):
        raise ValueError("plugin.json and VERSION must use base x.y.z semantic versions")
    if manifest_base != version_file:
        raise ValueError(f"version mismatch: manifest={manifest_base}, VERSION={version_file}")
    return manifest_base


def bump(version: str, kind: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if kind == "breaking":
        major, minor, patch = major + 1, 0, 0
    elif kind == "feature":
        minor, patch = minor + 1, 0
    elif kind == "fix":
        patch += 1
    else:  # pragma: no cover - argparse prevents this
        raise ValueError(f"unknown bump kind: {kind}")
    return f"{major}.{minor}.{patch}"


def update(plugin_root: Path, kind: str, summary: str) -> str:
    current = read_base_version(plugin_root)
    next_version = bump(current, kind)
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = next_version
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (plugin_root / "VERSION").write_text(next_version + "\n", encoding="utf-8")
    changelog = plugin_root / "CHANGELOG.md"
    existing = changelog.read_text(encoding="utf-8") if changelog.exists() else "# Changelog\n"
    entry = f"\n## {next_version} — {datetime.now(timezone.utc).date().isoformat()}\n\n- {summary.strip()}\n"
    changelog.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")
    return next_version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("feature", "fix", "breaking"))
    parser.add_argument("--summary", required=True, help="Human-readable change recorded in CHANGELOG.md")
    parser.add_argument("--plugin-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if not args.summary.strip():
        parser.error("--summary must not be empty")
    print(update(args.plugin_root.resolve(), args.kind, args.summary))


if __name__ == "__main__":
    main()
