# Codex Project Memory

This repository uses persistent context files so new Codex windows can recover
the project's state quickly.

## Required Startup

- Read this file first.
- Then read `PROJECT_CONTEXT.md`.
- Reply to the user in Chinese unless they ask otherwise.
- Check `git status --short --branch` before changing, staging, committing, or
  pushing.
- Stage explicit files only. This worktree contains many untracked probes,
  screenshots, caches, and reference artifacts.

## Repository Rules

- Remote: `https://github.com/zhongshiyu896-glitch/lingyi.git`
- Default branch: `main`
- Do not bulk-add all untracked files without explicit confirmation.
- Keep durable project facts in `PROJECT_CONTEXT.md` and update it after
  important environment, GitHub, deployment, or architecture changes.
- Prefer `gh` for GitHub auth and repository checks.

## Safety Notes

- Do not ask the user to paste GitHub tokens or passwords into chat.
- If GitHub auth is needed, use `gh auth login --web --clipboard`.
- If a commit is requested, summarize exactly which files were staged.
