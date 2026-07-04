# Prompt 3 — `ExtractionCache` interface

## Context

`GradientCoupledCompactionFunction` (a later prompt in this sequence) will
need to avoid repeating expensive per-point work — a noiseless downflow
integration plus a density-match root-find — when the same `(y, N)` query
point is requested more than once, e.g. by movie/profile-generation code
that reuses a fixed `y_sample` grid across many `N` frames. The cache should
be keyed on **identity** (`store_id` of the `y_value`/`efold_value`
involved), not floating-point proximity, which is exactly why `y_value` was
made a persisted, `store_id`-bearing concept in prompt 1.

This prompt only builds the cache abstraction itself — a lightweight
interface plus a dict-backed implementation — with no reference yet to what
it will cache (that comes with `GradientCoupledCompactionFunction`). The
point of taking this as its own prompt, rather than folding it into the
compute target that uses it, is so the storage backend can be swapped later
(e.g. for a Ray-object-store- or Redis-backed implementation, if the
in-memory version ever proves insufficient for cross-worker sharing)
without touching any call site.

**Note**: `ExtractionCache` is a plain in-memory utility, not a
`DatastoreObject` and not SQL-persisted. The four-registration-points
requirement for new `DatastoreObject` models (factories dict, `ClientPool`
batch size, `config/sharding.py` replicated/sharded + `read_table_config`)
does **not** apply to this prompt — there is nothing to register.

## Task

### 1. `Caching/ExtractionCache.py`

Create an abstract interface and a single concrete implementation:

```python
class ExtractionCache(ABC):
    @abstractmethod
    def get(self, key: Hashable) -> Optional[Any]: ...

    @abstractmethod
    def set(self, key: Hashable, value: Any) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...
```

- `get(key)` returns `None` if `key` has not been cached. Document
  explicitly that cached values must never themselves be `None` — callers
  cannot distinguish "absent" from "cached `None`" through this interface.
  Since the intended payload (`(zeta, r)` tuples of floats) can never
  legitimately be `None`, this is an acceptable simplification; note it in
  the docstring so it's a documented contract, not a silent trap for a
  future caller with different payload semantics.
- `InMemoryExtractionCache(ExtractionCache)`: backed by a plain `dict`.
  `get`/`set`/`clear` map directly onto `dict.get`/`__setitem__`/`clear`.
- Document in the class docstring that this implementation is **not**
  thread-safe and **not** shared across Ray worker processes — each
  worker/process gets its own independent cache. This is a known,
  deliberate limitation for now (see the follow-up discussion in
  `onion_model_planning.md` history), not something to work around in this
  prompt.
- No key-shape assumptions baked into the interface — `Hashable` is
  intentionally general. The specific key shape
  `(y_value.store_id, N_value.store_id)` is a decision for the code that
  *uses* this cache (`GradientCoupledCompactionFunction`, in a later
  prompt), not for the cache itself.

### 2. Tests

`tests/test_extraction_cache.py`:

- `get` on an empty cache returns `None`.
- `set` then `get` with the same key returns the stored value.
- `get` with a different key (even a similar one, e.g. a tuple differing in
  one element) returns `None`, not the value for a "close" key — this is
  meant to be a strict identity-keyed cache, no fuzzy matching.
- `set` twice with the same key overwrites (last write wins).
- `clear()` empties the cache; a subsequent `get` on a previously-set key
  returns `None`.
- Confirm `InMemoryExtractionCache` can be constructed and used purely
  through the `ExtractionCache` interface type (i.e. the test doesn't need
  to reach into `._store` or similar implementation detail to verify
  behaviour) — this is really a test that the abstraction is usable on its
  own terms, not just that the dict underneath works.

## Acceptance criteria

- [ ] `Caching/ExtractionCache.py` created with `ExtractionCache` (ABC) and
      `InMemoryExtractionCache`.
- [ ] Docstrings state the "cached values must not be `None`" contract and
      the "not thread-safe, not cross-process" limitation explicitly.
- [ ] No `DatastoreObject`/SQL/sharding changes in this prompt — this is a
      plain in-memory utility.
- [ ] Unit tests pass, covering miss/hit/overwrite/clear and distinct-key
      non-collision.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Add ExtractionCache interface and in-memory implementation`
