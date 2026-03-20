# Project context

This project was created to solve a simple problem:

Continue working with Codex across multiple machines using local state sync.

Key decisions:

* Avoid deep integration with Codex
* Do not rely on undocumented internals
* Keep implementation simple
* Prefer safety over complexity
* Focus on "after close" sync
* Stop on two-sided file conflicts and require manual resolution + rerun
* Keep logging configurable (`text|json|logfmt`) with 7-day default retention
* In verbose mode (`-v`), print tracked Codex processes for plan/sync/restore diagnostics
* Use explicit CLI exit codes for automation and CI

This is intentionally a lightweight developer utility, not a full platform.
