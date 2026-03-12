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

## [ERR-20260312-001] rg-shell-command

**Logged**: 2026-03-12T04:15:00Z
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
`rg.exe` is present in this Codex desktop PowerShell environment but cannot be executed successfully.

### Error
```text
程序“rg.exe”无法运行: Access is denied
```

### Context
- Command attempted: `rg --files`
- Environment: PowerShell on Windows inside Codex desktop

### Suggested Fix
Fall back to PowerShell-native file inspection commands when `rg` is blocked in this environment.

### Metadata
- Reproducible: yes
- Related Files: D:\Projects\bili-atelier

### Resolution
- **Resolved**: 2026-03-12T04:16:00Z
- **Commit/PR**: pending
- **Notes**: Switched to `Get-ChildItem` and direct file reads for repository inspection.

---
