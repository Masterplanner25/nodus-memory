# Contributing to nodus-memory

## Note on history

An earlier version of this repo provided nodus-lang bindings
(`attach_to_runtime`, `.nd` script import). The current package is the
standalone Tier 2 memory library. The old adapter is in git history.

## Setup

```bash
git clone https://github.com/Masterplanner25/nodus-memory.git
cd nodus-memory
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -q
```

## Code style

- Python 3.11+
- No required external dependencies (stdlib only)
- `MemoryStore` and `EmbeddingProvider` are protocols — backends satisfy
  them by structure, not inheritance
- `update_feedback` mutates the node in-place — keep this invariant
- Auto-detection of `nodus-native-memory-engine` for hot-path scoring
  (import guard via `try/except`)

## Submitting changes

1. Fork the repo and create a branch from `main`
2. Add tests for any new behaviour
3. Ensure `pytest tests/ -q` passes
4. Open a pull request with a description of what changes and why
