# Plugin development workflow

## Capability versions

`plugins/chan-quant/.codex-plugin/plugin.json` and `plugins/chan-quant/VERSION` must contain the same base `x.y.z` version. Use:

```bash
python3 plugins/chan-quant/scripts/bump_version.py feature --summary "add a new research capability"
python3 plugins/chan-quant/scripts/bump_version.py fix --summary "handle malformed backend output"
python3 plugins/chan-quant/scripts/bump_version.py breaking --summary "change a Tool response contract"
```

The feature command increments the minor component and resets patch to zero. The script updates the manifest, VERSION, and CHANGELOG together. A `+codex.<cachebuster>` suffix is reserved for local reinstall discovery and never replaces the base capability version.

## Parallel worktrees

Developer tooling can create isolated task worktrees from a clean base checkout:

```bash
python3 plugins/chan-quant/scripts/create_worktrees.py \
  --repo /absolute/path/to/chan-quant \
  --base main \
  --root /absolute/path/to/chan-quant-worktrees \
  --task mcp-adapter --task skills --task validation
```

Each task receives its own `codex/plugin/<task>` branch and directory. The helper refuses a dirty base, existing worktree path, or existing branch; it never merges, pushes, deletes, or changes the plugin at runtime. Verify each task branch before a separately authorized local merge.

