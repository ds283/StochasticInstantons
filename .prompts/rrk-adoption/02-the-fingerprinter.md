# Prompt 02 — the fingerprinter

**Campaign:** [`README.md`](README.md) · **Board items:** **F1**–**F4** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, after the user's rulings (README §6). Its orchestrator note, written after
01's review, hands it 01's counts and governs where it differs from this file.
**Gate:**
- 01 landed and reviewed, with the gate "Pin" holding (board §2);
- on branch `rrk-adoption`, no tracked change in `git status`;
- no SI Ray process is running (`ray_cluster.sh status`). You start no cluster; the integration
  tests start private, in-process Ray instances of their own (`RAY_ADDRESS=local`).

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. A small module after the siblings', a guard test from a published
recipe, and a golden test on a temporary store built by an existing harness.

**Read first:**

1. [`README.md`](README.md): §0.3 ("The registry"; "The tests"), §2.2 (02's charter), §5, §6.2
   (P5, P6, P11).
2. RunRegistryKit at `v0.2.0` (read, never edit):
   - `runregistrykit/fingerprint.py`: the protocol, `DatastoreKitFingerprinter`,
     `load_fingerprinter`;
   - `docs/adoption/README.md` §6, "The Q5 guard", and its addendum at the end, "The Q5 guard under
     DatastoreKit `v0.5.0`": the recipe, and the one condition that leaves out an empty
     `extra_values` (P5);
   - its `README.md`, "The store layer".
3. The models (read, never edit):
   - ChamPBH at `807f175`: `config/fingerprint.py`;
     `ObjectFactories/tests/test_fingerprint_format_guard.py`;
     `ObjectFactories/tests/test_store_fingerprint_golden.py` (`TestGolden`,
     `TestConfigFingerprint`); its golden file under `ObjectFactories/tests/data/`, and its prompt 02's
     results note (`.documents/rrk-adoption/` there, or its `prompts/rrk-adoption/logs/`);
   - SecondaryGWKit at `216e44d`: `config/fingerprint.py`, and its guard and golden tests.
4. This repository:
   - `config/datastore.py` (`factories`);
   - `tests/test_inventory_specs.py`: coverage (24 classes, 22 spec definitions) and
     `EXPECTED_SPECS`;
   - `tests/test_inventory_store.py`: `_STORE_SCRIPT` and the `store` fixture, which build a
     two-shard store of synthetic rows, every class present (the gradient branch with and without
     full values), through the package's pool in a subprocess under a private Ray, and close it;
   - `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`'s `inventory_spec` (its
     `extra_values`);
   - `runregistrykit.toml` and `tests/test_registry_config.py`, as 01 left them.

---

## 1. What is wanted

The store layer can take, compare and record the fingerprint of an SI store. What goes into the
fingerprint is this repository's: the factories' inventory specs, the registry and a format number.
A spec that changes without the number moving fails a test, naming the class.

### 1.1 The items

- **F1 — `config/fingerprint.py`**, after the siblings':
  - a module docstring saying who does what (the specs and the format are SI's; encoding and
    digest are DatastoreKit's; when and where a fingerprint is taken is RunRegistryKit's), and
    naming the test that guards the format;
  - `FINGERPRINT_FORMAT = 1`, the first of a history, with a comment saying when the number
    moves: a change to any spec, or to the registry's classes or order. Golden files are never
    overwritten; a format change adds one beside the old;
  - `SPEC_DIGESTS = {1: [[class, sha256], …]}`, one pair per class with a spec, in registry order,
    computed by F3's functions and pasted in;
  - `fingerprinter = DatastoreKitFingerprinter(factories, FINGERPRINT_FORMAT)`.

  Importing it loads nothing that `config.datastore` does not already load: check it by
  `sys.modules` before and after, and say how.
- **F2 — the config names it.** `runregistrykit.toml` gains:
  ```toml
  [stores]
  fingerprinter = "config.fingerprint:fingerprinter"
  ```
  `tests/test_registry_config.py`'s expected set of keys gains `[stores]` (01 wrote it to be
  extended; this is the one edit of an existing test this prompt makes, and it is 01's test).
- **F3 — `tests/test_fingerprint_format_guard.py`** (default selection, no Ray), the recipe with the
  `v0.5.0` amendment (P5):
  - `plain(value)`: dataclasses as objects of their fields, **leaving out a field named
    `extra_values` whose value is empty**; sequences as lists; and every mapping key written as its
    own JSON, so that `0` and `"0"` stay apart;
  - `spec_digests(factories)`: `[[name, sha256(canonical_json(plain(spec)))], …]` over
    `datastorekit.store_inventory.inventory_specs(factories)`, in registry order.

  The tests:
  - `spec_digests(factories) == SPEC_DIGESTS[FINGERPRINT_FORMAT]`. A failure names the classes
    that differ and says to bump the format and add a pin;
  - a pin exists for the current format;
  - **the key keeps its type**: a stand-in `Parent` whose `types` is keyed by `0`, and one keyed by
    `"0"`, give different digests (SI has no polymorphic `Parent.types` key of type `int` today; the
    test guards the recipe, as the siblings' do);
  - **the amendment**: a stand-in spec with `extra_values={}` gives the digest of the same spec with
    the field removed from `plain`'s output, and one with a non-empty `extra_values` does not.

  The count of pairs is the number of classes with a spec. State it, and that it equals
  `test_inventory_specs`'s (24 classes, measured at 10b).
- **F4 — `tests/test_store_fingerprint_golden.py`** (`integration`, P11).
  - **The golden store** is built by `tests/test_inventory_store.py`'s `_STORE_SCRIPT`, run as its
    `store` fixture runs it (P6): import the script (and, if they import cleanly, the fixture's
    helpers) from that module, **without modifying it**. If it cannot be imported cleanly, copy the
    script into the new module and record it as a deviation. The store lives in a `tempfile`
    directory and is closed before it is read.
  - **`TestGolden`.** `config.fingerprint.fingerprinter.take(primary, taken={})`; `problems` is
    empty; the fingerprint, with `taken` removed, equals the committed golden file
    `tests/data/store_fingerprint_rrk-adoption-02.json`. The file is written once by this prompt,
    from the store's fingerprint, and never overwritten. The test's docstring says how a later
    format adds a file beside it.
  - **The golden file is reproducible.** Build the store twice, in two runs of the test process,
    and show both fingerprints equal before committing the file. If they differ, stop: the build is
    not deterministic, and the golden test would be flaky.
  - **`TestConfigFingerprint`** (it needs no store, so it is in the default selection: mark the
    class, not the module):
    - `runregistrykit.fingerprint.load_fingerprinter(find_client_root(client_root=<root>))`
      returns `config.fingerprint.fingerprinter`, an instance and a `Fingerprinter`;
    - its format is `FINGERPRINT_FORMAT` and its factories are `config.datastore.factories`.
  - **The command line, once.** `./venv/bin/python -m runregistrykit --client-root <root> store
    fingerprint <the temporary store> --runs-root <a temporary runs root>`, by subprocess. It prints
    the golden digest and exits as RunRegistryKit's README says for a store with no sidecar.
    `--runs-root` keeps the command from reading the repository's `var/runs`. Record its output.

  Nothing under `var/` is opened or created by these tests.

---

## 2. Verification

1. **Before any edit:** both suites at the counts 01 handed on.
2. **After:** both suites (the default selection gains F3 and `TestConfigFingerprint`;
   `integration` gains `TestGolden`); `./venv/bin/python -m runregistrykit list` still shows no
   run.
3. **The golden file's provenance**: the results note records how it was written (the command, or
   the few lines that wrote it), its SHA-256, its overall `digest`, and the two reproducibility
   builds' digests.
4. **Deliberate breakages** (README §5: each recorded as a diff, never committed). Each must fail
   the named test:
   - a leaf added to one spec, with no bump: F3, naming the class;
   - `FINGERPRINT_FORMAT = 2` with no new pin: F3;
   - `GradientCoupledInstanton`'s `extra_values` emptied: F3 names that class and no other;
   - the amendment's condition removed from `plain`: F3's amendment test;
   - one value changed in the golden store's rows: `TestGolden`;
   - `fingerprinter` named as the class in the config: `TestConfigFingerprint` (the loader refuses
     a class).

## 3. Acceptance

1. F1–F4 as §1.1 says.
2. §2's checks in the results note, each with its command and output.
3. Suites: the counts 01 handed on, plus the new tests in their selections.
4. **One commit**, with the results note `.documents/rrk-adoption/02-the-fingerprinter.md`. The
   board: row 02, F1–F4, the gate "Fingerprint", and a `### 5.3 After prompt 02 (<date>)`. Write
   "this commit" where the SHA goes.

## 4. Stop conditions: stop and ask

- `read_inventory` reports a problem on the golden store. The rows or a spec are wrong; it is not
  this prompt's to change either.
- The count of specs differs from `test_inventory_specs`'s.
- The golden store's fingerprint differs between two builds.
- `load_fingerprinter` or `store fingerprint` behaves otherwise than RunRegistryKit's README says.
  That would be a package defect, reported there, never worked around (README §5).
- A spec, a factory or the registry would need a change.
- Anything would need an edit outside §5's list.

## 5. What this prompt does not do

- **Files it changes:**
  - `config/fingerprint.py` (new);
  - `runregistrykit.toml` (`[stores]`);
  - `tests/test_registry_config.py` (the expected keys);
  - `tests/test_fingerprint_format_guard.py` and `tests/test_store_fingerprint_golden.py` (new);
  - `tests/data/store_fingerprint_rrk-adoption-02.json` (new);
  - this board, and the results note.
- It changes no spec, factory or registry entry, and no other test. `tests/test_inventory_specs.py`'s
  docstring still says SI adopts RunRegistryKit "after this campaign"; that is 05's (P12).
- It opens no store but its temporary ones, starts no cluster, and creates nothing under `var/`.

**One commit** in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
