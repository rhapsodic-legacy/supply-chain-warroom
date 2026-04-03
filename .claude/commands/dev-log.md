---
description: Append a timestamped entry to the development log documenting what was built.
argument-hint: [summary of what was built]
---

Append an entry to docs/DEVELOPMENT.md documenting the current development session.

## Steps

1. Read docs/DEVELOPMENT.md for the current log format
2. Use git log and git diff --stat to determine what changed recently
3. Create a new entry with:
   - ISO 8601 timestamp
   - Summary (from $ARGUMENTS or inferred from git changes)
   - Files created/modified
   - Claude Code techniques used (skills, subagents, hooks)
   - Challenges and resolutions
4. Append the entry to docs/DEVELOPMENT.md
5. Print the entry for review

## Entry Format

```
## YYYY-MM-DD HH:MM — [Summary]

**What was built:** [Description]

**Files changed:** [List]

**Claude Code techniques:**
- [Technique]

**Challenges:** [Any issues and resolutions]
```
