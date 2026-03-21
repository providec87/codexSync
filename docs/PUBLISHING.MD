# Publishing Checklist (GitHub)

## 1. Pre-publish safety checks

1. Confirm local-only constraints are documented in `AGENTS.MD` and `README.MD`.
2. Confirm only `config.example.toml` is tracked (no machine-specific config).
3. Confirm temp/cache/test runtime folders are ignored by `.gitignore`.

## 2. Prepare repository

Run from project root:

```powershell
git init
git add .
git status
```

Review staged files and ensure the following are NOT staged:

- `config.toml`
- `config2.toml`
- `.idea/`
- `__pycache__/`
- local runtime folders (`logs/`, `backups/`, `sync/`, `state/`, `.tmp*`)

## 3. First commit

```powershell
git commit -m "chore: prepare codexSync MVP for GitHub publication"
```

## 4. Connect GitHub remote and push

```powershell
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 5. Verify after push

1. Open repository on GitHub.
2. Confirm CI workflow `CI` is running in `Actions` for both `windows-latest` and `macos-latest`.
3. Confirm README renders correctly.
4. Confirm no local/private files were uploaded.
