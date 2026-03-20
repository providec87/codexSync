# Contributing Guide

Thank you for contributing to codexSync.

## Inbound = Outbound Licensing

By submitting a contribution (code, docs, tests, or other material), you agree that your contribution is licensed under `GPL-3.0-or-later` for the open-source version of this project.

## Contributor License Agreement (CLA)

To keep dual licensing possible (`GPL-3.0-or-later` + commercial licenses), contributors must also grant the maintainers the right to relicense their contributions.

Before your first contribution is accepted, you must agree to the terms in [CLA.md](./CLA.md).

## Contribution Workflow

1. Fork the repository.
2. Create a branch for your change.
3. Keep changes focused and documented.
4. Add or update tests when behavior changes.
5. Open a pull request.

## Quality and Safety Expectations

Given the project scope (local state sync), contributions should preserve these safety properties:

- Never write state while Codex is running.
- Always create a backup before overwrite.
- Exclude temporary/lock/cache files.
- Fail safely when state is uncertain.

## Legal Notice

Do not submit code you do not have the right to contribute.
By submitting, you confirm you have the legal authority to license your contribution under the terms above.
