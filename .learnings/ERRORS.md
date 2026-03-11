# Errors

## [ERR-20260311-001] powershell-shell-command

**Logged**: 2026-03-11T12:02:00Z
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
PowerShell in this environment does not accept `&&` as a command separator.

### Error
```text
The token '&&' is not a valid statement separator in this version.
```

### Context
- Command attempted: `git add article_jina.txt wechat_article.html && echo done`
- Environment: PowerShell on Windows inside Codex desktop

### Suggested Fix
Use separate commands or PowerShell-compatible sequencing instead of shell separators like `&&`.

### Metadata
- Reproducible: yes
- Related Files: D:\Projects\bili-atelier

### Resolution
- **Resolved**: 2026-03-11T12:03:00Z
- **Commit/PR**: pending
- **Notes**: Switched back to single-purpose PowerShell commands for staging and follow-up steps.

---
