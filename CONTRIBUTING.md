# Contributing

Thanks for helping. Small, focused pull requests are easiest to review.

## Setup

```bash
uv sync                     # creates .venv with Python 3.12 and dev tools
uv run pre-commit install   # runs ruff on every commit
```

## Before opening a pull request

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

CI runs the same commands and must stay green.

## Rules

- **Tests run offline.** Use small fixture files in `tests/fixtures/`. Never call live
  sources from a test.
- **Raw data is never edited.** Every download is logged in a manifest (URL, timestamp,
  SHA-256). Fixes happen in later layers.
- **No data in git.** Downloaded and generated files go in `data/` (ignored).
- **Join on validated codes only.** Never merge entities by name.
- **Privacy.** Never publish a natural person's tax code (16 characters). No standalone
  person pages.
- **Neutral wording.** Indicators are "statistical signals", described next to the peer
  average. Avoid words like "suspicious" or "fraud".
- **Record decisions.** Choices someone might question later get an ADR in `docs/adr/`.

## License

By contributing you agree that your code is licensed under AGPL-3.0.
