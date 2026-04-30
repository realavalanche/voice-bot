# MemPalace — Auto-Managed

This directory is **automatically maintained** by autosetup.

## What happens automatically

| Trigger | Action |
|---------|--------|
| `autosetup apply` | `pip install mempalace` → `mempalace init .` → `mempalace mine .` |
| Agent request / manual run | `bash .autosetup/scripts/update-graph.sh` re-mines memory |

## Manual controls

```bash
# Re-mine memory from codebase
mempalace mine .

# Wake up memory context for current session
mempalace wake-up

# Watch mode: auto-update on any file change
bash .autosetup/scripts/watch.sh
```
