# Tool Usage Learnings

This file is intended to be used by an LLM such as Claude.

## UV Package Manager

- Use `uv run` to run Python tools without activating virtual environments
- For formatting: `uv run ruff format .`
- For type checking: `uv run pyright`
- For upgrading packages:
  - `uv add --dev package --upgrade-package package` to upgrade a specific package
  - Don't use `@latest` syntax - it doesn't work
  - Be careful with `uv pip install` as it may downgrade packages

## Git and GitHub CLI

- When using gh CLI for PRs, always quote title and body:
  ```bash
  gh pr create --title "\"my title\"" --body "\"my body\""
  ```
- For git commits, use double quotes and escape inner quotes:
  ```bash
  git commit -am "\"fix: my commit message\""
  ```

## Python Tools

### Ruff
- Handles both formatting and linting
- For formatting: `uv run ruff format .`
- For checking: `uv run ruff check .`
- Common issues:
  - Line length (default 88 chars)
  - Import sorting
  - Unused imports

### Pyright
- Type checker
- Run with: `uv run pyright`
- Version warnings can be ignored if type checking passes
- Common issues:
  - Optional types need explicit None checks
  - String operations need type narrowing

## Best Practices

1. Always check git status and diff before committing
2. Run formatters before type checkers
3. When fixing CI:
   - Start with formatting issues
   - Then fix type errors
   - Then address any remaining linting issues
4. For type errors:
   - Get full context around error lines
   - Consider optional types
   - Add type narrowing checks when needed
