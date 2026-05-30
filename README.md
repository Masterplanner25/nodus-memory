# nodus-memory

Persistent, multi-tenant, searchable memory for Nodus agents.

## Quick start

```python
from nodus_memory import MemoryStore, MemoryConfig, attach_to_runtime
from nodus import NodusRuntime

store = MemoryStore(MemoryConfig(tenant_id="alice"))
store.put("greeting", "hello world")
print(store.get("greeting"))  # "hello world"

# Use from Nodus scripts
runtime = NodusRuntime()
attach_to_runtime(runtime, store)
result = runtime.run_source('''
import "nodus-memory"
share("note", "remember this")
let v = recall_from("note")
print(v)
''')
```

## Features

- In-process and SQLAlchemy persistence backends
- Tag-based and path-prefix retrieval
- Causal chain linking
- Scoring and feedback loops
- Nodus language bindings (`recall_from`, `share`, `forget`, `tag`, `link`, `recall_all`)
- Pluggable embedding provider (pgvector in v0.2)
- Tenant isolation

## Installation

```
pip install nodus-memory                   # in-process backend only
pip install "nodus-memory[db]"             # + SQLAlchemy persistence
pip install "nodus-memory[db,embed]"       # + numpy for cosine similarity
```

## Status

v0.1.0 — PREPARED, NOT RELEASED. Publication waits for coordinated launch.
