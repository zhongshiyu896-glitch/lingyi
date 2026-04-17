# Project Context

Last updated: 2026-04-17

## Purpose

This file is the durable memory for Codex windows working in this repository.
Future threads should read it before making decisions.

## Current GitHub State

- Local repository root: `/Users/hh/Documents/Playground 2`
- GitHub repository: `https://github.com/zhongshiyu896-glitch/lingyi`
- Git remote `origin`: `https://github.com/zhongshiyu896-glitch/lingyi.git`
- Branch: `main`
- Initial pushed commit: `9781e75 first commit`
- `README.md` has been pushed to `origin/main`.
- GitHub CLI is installed and authenticated as `zhongshiyu896-glitch`.

## Important Worktree State

- The worktree has many untracked files, including screenshots, JSON probes,
  Python scripts, ERPNext/Frappe folders, reports, and temporary artifacts.
- Do not run `git add .` or bulk-commit the worktree unless the user explicitly
  asks for that.
- When committing, stage only the named files required for the current task.

## Recent System Fixes

- On 2026-04-17, repeated macOS "missing keychain" popups were traced to a
  missing default/login keychain.
- A new login keychain was created, set as default/login, and verified with a
  test password item.
- GitHub CLI login was completed through browser/device-code OAuth and stored in
  the macOS keyring.

## Persistent Memory Plan

- Global memory lives in `/Users/hh/.codex/AGENTS.md`.
- Project rules live in `AGENTS.md`.
- Project facts live in this file.
- Future Codex windows should update this file when durable facts change.
