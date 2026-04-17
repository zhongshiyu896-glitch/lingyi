# Codex Project Memory

This repository uses persistent context files so new Codex windows can recover
the project's state quickly.

## Required Startup

- Read this file first.
- Then read `CORE_MEMORY.md`.
- Then read `PROJECT_CONTEXT.md` only when more background is needed.
- Reply to the user in Chinese unless they ask otherwise.
- Check `git status --short --branch` before changing, staging, committing, or
  pushing.
- Stage explicit files only. This worktree contains many untracked probes,
  screenshots, caches, and reference artifacts.

## Repository Rules

- Remote: `https://github.com/zhongshiyu896-glitch/lingyi.git`
- Default branch: `main`
- Do not bulk-add all untracked files without explicit confirmation.
- Keep canonical durable facts in `CORE_MEMORY.md`.
- Keep supporting context in `PROJECT_CONTEXT.md`.
- Update memory after important environment, GitHub, deployment, architecture,
  or long-lived workflow changes.
- Prefer `gh` for GitHub auth and repository checks.

## Memory Hygiene

- `CORE_MEMORY.md` should stay short enough to read every time.
- Add only facts that will affect future choices or prevent repeated mistakes.
- Remove stale, duplicated, or low-value facts when updating memory.
- Do not store command transcripts, temporary probes, screenshots, old failed
  attempts, or implementation chatter as durable memory.
- If a detail is useful only for the current answer, mention it in the final
  response instead of writing it into memory.

## Safety Notes

- Do not ask the user to paste GitHub tokens or passwords into chat.
- If GitHub auth is needed, use `gh auth login --web --clipboard`.
- If a commit is requested, summarize exactly which files were staged.
