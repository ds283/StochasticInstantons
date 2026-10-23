# The packages' scripts at the commits the G4 drafts name (prompt 12, 2026-10-23)

Each script run from its package's root with its own venv (DatastoreKit `2900d82`, RayPoolKit `17029d9`, both clean),
reading SI through `git` only. The full output at `47c0a77` is `12-datastorekit-measure_client_imports.md` and
`12-raypoolkit-measure_client_pools.md`.

**DatastoreKit `docs/extraction/measure_client_imports.py si --commit <sha>`**

| SI commit | `.py` files read (unparsed) | layer imports | layer string literals | `import_module` / `__import__` | factory-module imports |
|---|---|---|---|---|---|
| `f4da58f` (09) | 197 (0) | 0 | 0 | 0 | 25 |
| `2179854` (11) | 201 (0) | 0 | 0 | 0 | 25 |
| `18b490a` | 201 (0) | 0 | 0 | 0 | 25 |
| `47c0a77` (12's start) | 201 (0) | 0 | 0 | 0 | 25 |

The seven layer modules are absent at each; the two `__init__.py` are present and empty.

**RayPoolKit `docs/adoption/measure_client_pools.py si --commit <sha>`**

| SI commit | `RayTools/` | imports (private) | `import_module` calls | string literals | `RayWorkPool(...)` calls | verdicts | non-`.py` lines | test modules |
|---|---|---|---|---|---|---|---|---|
| `ef13445` (04) | absent | 0 (0) | 0 | 2 | 16 (12 with `compute_handler=None`, 4 with one) | `constructs` 16 | 387 | 1 |
| `0527480` (07) | absent | 0 (0) | 0 | 2 | 16 (12, 4) | `constructs` 16 | 397 | 1 |
| `2179854` (11) | absent | 0 (0) | 0 | 2 | 16 (12, 4) | `constructs` 16 | 402 | 1 |
| `18b490a` | absent | 0 (0) | 0 | 2 | 16 (12, 4) | `constructs` 16 | 402 | 1 |
| `47c0a77` (12's start) | absent | 0 (0) | 0 | 2 | 16 (12, 4) | `constructs` 16 | 421 | 1 |

The non-`.py` count moves with every records commit, since `.prompts/` and `.documents/` are counted.
