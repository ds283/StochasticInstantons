# Brief: an `InventorySpec` that can count more than one value table

**For:** the agent that plans a campaign in DatastoreKit (`/Users/ds283/Documents/Code/DatastoreKit`)
to release the next `datastorekit`, under DatastoreKit's `CLAUDE.md` and its campaign conventions.
The version number is DatastoreKit's to choose (§4).
**Written:** 2026-10-21, from a Claude Code session in StochasticInstantons (SI), at the user's
request, after SI's adoption campaign's prompt 10 had ported SI's inventory to `inventory_spec`
(`.prompts/dk-and-rpk-migration/` in SI; its board's `[gci-value-table-outside-the-inventory]`).
**Trees:** DatastoreKit at `38ebb9f` (`v0.4.0` is `c8570e8`); SI at `d0ce59c` (its specs landed at
`e2c7b22`); ChamPBH at `7055532` and SecondaryGWKit (SGK) at `031bcb4`, read through `git`.

**This brief is evidence to check, not a specification** (DatastoreKit `CLAUDE.md` invariant 7).
The user's request, in §1, is a request. Everything else is a finding with its citation, or a
recommendation marked **Advice:**. Where this brief and DatastoreKit's own records disagree, the
records are right, and the disagreement is worth reporting back. The campaign's name, its decision
numbers, its shape, the new field's name and the version are DatastoreKit's to choose.

## 1. What is asked, and who asked

**The user's request (2026-10-21):** the release that DatastoreKit's `fingerprint` campaign left
out of `v0.4.0` "until SI's prompt 10 settles it and the user asks"
(`prompts/fingerprint/README.md:204-205`; SGK's brief, `datastorekit-fingerprint-brief.md:118-121`).
SI's prompt 10 has settled it, and this is the ask.

**The change asked for.** A factory's `InventorySpec` can name **more than one value table**, and
the inventory counts the value rows of each, per record, as it counts the one table of `values`
today. A store's fingerprint then sees every value table a class owns: their counts, and their
orphans as named problems.

**What does not change.** For every spec that declares no more than it does today, every `Record`
is the same, byte for byte, in `canonical_json`. So every fingerprint any client has recorded stays
valid (§4, "The compatibility property").

## 2. Why it is needed, and why only by SI

**The slot.** `InventorySpec.values` is one `(value table, its column naming this class's serial)`
pair, or `None` (`store_inventory.py:293-303` at `v0.4.0`; contract §4's `values` row). `read_records`
counts it with one `GROUP BY` per shard (`:644-667`), and the count is `Record.value_count`
(`:179-193`, `:773`), which is in every record's canonical line and so in the fingerprint
(`store_fingerprint.py`, contract §9.7). Rows of the value table that name no row of the class are
an `orphan-value` problem (`:656-667`). Nothing else in the package reads `values`: `git grep` of
`datastorekit/` less `tests/` at `v0.4.0` finds it only at `store_inventory.py:311`
(`InventorySpec.keywords`).

**SI's class with two child tables.** `GradientCoupledInstanton` (sharded on `delta_Nstar`) owns:
- **`GradientCoupledInstantonProfile`** (`parent_serial`, one row per collocation node): the radial
  profile, the science output, written for every row
  (`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:594-605` at `e2c7b22`);
- **`GradientCoupledInstantonValue`** (`instanton_serial`, composite key with `N_serial`): the
  solution's fields on the e-fold grid, written only when `store_full_values` is set, which the
  scalars-only pipeline (`main.py --no-store-values`) clears (`:580-592`; the factory at `:676`).

Both name their owner by foreign key. SI's prompt 10 gave the slot to the profile, which every row
has (`:147-181`, `values=("GradientCoupledInstantonProfile", "parent_serial")` at `:180`), and
excluded the value table, by name and with that reason, in its coverage test
(`tests/test_inventory_specs.py:208-213`, `EXCLUDED`). So **`read_inventory`, and every fingerprint
taken through it, cannot see `GradientCoupledInstantonValue`**: not its counts, and not an orphan
among its rows. A store whose gradient value rows were lost, or never written when they should have
been, fingerprints the same as one that has them.

**The other 29 entries of SI's registry need nothing.** Every other class SI covers has at most one
value table (24 specs, 5 tables read through a `values` slot, 1 excluded; SI's
`tests/test_inventory_specs.py:409-412`).

**ChamPBH and SGK need nothing.** By `git grep` at their `HEAD`s: ChamPBH's coverage test excludes
nothing (`ObjectFactories/tests/test_inventory_specs.py:82`, `EXCLUDED = {}`); SGK's seven specs with
a value table name one each (`values=(…)` at `ObjectFactories/BackgroundModel.py:908`,
`GkNumericIntegration.py:651`, `GkSource.py:869`, `GkWKBIntegration.py:981`,
`QuadSource.py:561`, `TkNumericIntegration.py:653`, `TkWKBIntegration.py:976`). So the release
must leave both untouched, including what their recorded fingerprints say.

**Why now.** SI has recorded no fingerprint yet: it adopts RunRegistryKit after its migration
campaign (SI's campaign README §7). If SI pins the release before its first recorded fingerprint,
no fingerprint SI ever records lacks the table. Later, SI's fingerprints would change when it adds
the table to its spec, and SI would bump its own `fingerprint_format` (contract §9.7: a change to a
client's specs is that client's format, never `ENCODING_FORMAT`). That works, but the earlier the
better.

## 3. What to check before planning

The brief's findings, to be measured again at DatastoreKit's `HEAD`:
1. **`values` is read in one place** (§2). Check that no other module (`store_reader`,
   `SQL/schema`, `SQL/ShardedPool`) reads `InventorySpec` fields beyond `dependencies()` and the
   parents (`schema.dependent_tables`, `:359`, reads the specs' `dependencies()`). A value table
   names its owner by foreign key, so `dependent_tables`' answer does not depend on the spec
   declaring it (its docstring says so); check that it stays so.
2. **Who reads a `Record`.** In the package: `canonical_json` and `identity` (`:195-200`), `_combine`'s
   replicated comparison (on `canonical_json`) and its duplicate check (on `identity`, which holds
   no count), `store_fingerprint.fingerprint_of` and `listing_lines` (canonical lines). In the
   clients: each `tools/inventory_report.py` reads `record.value_count` by attribute (SI's, at
   `e2c7b22`; ChamPBH's and SGK's of the same name). A new attribute with a default breaks none of
   these.
3. **The golden.** `datastorekit/tests/data/store_fingerprint-neutral-1-encoding-1.json` pins the
   neutral client's fingerprint. A design that keeps existing records byte-identical leaves it
   valid, and that is a test of the compatibility property, provided the neutral client's existing
   classes are not changed (§4, tests).
4. **`ENCODING_FORMAT`'s rule** (`store_fingerprint.py:38-64`; contract §9.7). Its first sentence
   ("any change that can make the same store, read with the same specs and the same client format,
   give a different fingerprint") is not met by the design in §4: an unchanged spec gives an
   unchanged record. Its item (1) ("a change to … `Record.as_json`'s fields") reads, to the letter,
   as met. Which governs is DatastoreKit's to decide and record (§4, "The version").
5. **Pickling and Ray.** The inventory crosses no actor and starts no Ray (`read_inventory`'s
   docstring); a spec is data. Nothing here touches the pool.

## 4. What a release would carry

**Advice**, for DatastoreKit to adopt or change.

**The compatibility property** (the one requirement this brief would hold the design to): a spec
that declares no extra value table gives records whose `canonical_json` is unchanged. Two designs:

- **Recommended: keep `values` and `value_count` as they are, and add beside them.**
  - `InventorySpec` gains one defaulted field, e.g. `extra_values: Mapping[str, Tuple[str, str]] =
    {}`: a name for each further value table (a field name the client chooses, e.g. `"fields"`) →
    `(value table, its column naming this class's serial)`, read exactly as `values` is.
  - `Record` gains one defaulted field, e.g. `extra_value_counts: Mapping[str, int] = {}`: per
    declared name, the count of that table's rows naming the record's row (0 where none).
  - `Record.as_json` includes it **only when the class declares any**, under a key of its own; a
    record of any other class has exactly today's four keys. The replicated comparison then covers
    the extra counts, since it compares `canonical_json`.
  - Each extra table is counted with one `GROUP BY` per shard, and its orphans are an
    `orphan-value` problem (the existing name, whose text already names the table), so problem
    counts by name keep their meaning.
  - `keywords()` passes the new field to `read_records`, which takes it as a keyword, defaulted.
- **Not recommended: `values` becomes a sequence or a mapping, and `value_count` a mapping.**
  Cleaner, but it changes every record of every client that declares a value table (SGK seven
  classes, ChamPBH three, SI five), so every recorded fingerprint differs, `ENCODING_FORMAT` is
  bumped by its first sentence, and every client must recompute. If DatastoreKit prefers it, the
  release says so in every client's addendum.

**Validation**, at `inventory_classes` (or at construction), each a `ValueError` as today's
refusals are: an extra table that is also the `values` table; the same table named twice; an empty
name. A missing table or column fails as `values` does today (`KeyError` when read); whether to
check that the column is a foreign key to the owner is DatastoreKit's (today's `values` is not
checked; SI's own test checks its specs' value columns, `tests/test_inventory_specs.py:351-358`).

**The tests**, in DatastoreKit's suite (no client imported), on a **new** neutral class or registry
so that the existing neutral classes, and the golden, stay as they are:
1. A class with `values` and two extra value tables: each record's counts, 0 where a table has no
   rows for it; a class declaring none has `extra_value_counts == {}` and today's `as_json` keys.
2. Orphans in an extra table: an `orphan-value` problem naming that table, on the right shard.
3. **The golden** (`store_fingerprint-neutral-1-encoding-1.json`) passes unchanged: existing
   records are byte-identical.
4. A replicated class whose extra count differs between shards: `replicated-divergence`.
5. Two stores that differ only in an extra table's rows: different fingerprints, and
   `compare_fingerprints` names the class.
6. The validation refusals above, each by its message.
7. `dependent_tables` with and without the extra table declared: the same answer.

**The documents.**
- `docs/client-contract.md`: a §9 subsection for the change; §4's table gains a row for the new
  field, and `Record`'s fields are stated where the contract states them. §1–§9.7 stay as written
  (invariant 6).
- `store_fingerprint.py`'s `ENCODING_FORMAT` comment, if DatastoreKit decides item (1) should say
  how an added, defaulted, omitted-when-empty field is treated.
- `docs/adoption/stochasticinstantons.md`: an addendum saying what SI does (§5).
  `docs/adoption/champbh.md` and `docs/adoption/secondarygwkit.md`: an addendum each, saying that
  nothing changes for that client and that its recorded fingerprints stay valid; it may stay on its
  pin.
- `PROVENANCE.md`, `README.md` ("Status", "Changes"), the version in `pyproject.toml`, and the
  campaign's own verification record, as the `v0.3.0` and `v0.4.0` releases did.

**The version.** The change adds to the public API and, under the recommended design, changes no
existing record. So `ENCODING_FORMAT` stays 1 if DatastoreKit reads its rule by the first sentence,
and the version is a minor one (`v0.5.0`, say). If DatastoreKit chooses the other design, or reads
item (1) to the letter, `ENCODING_FORMAT` becomes 2, a new golden is added beside the old, and the
release says so to every client (contract §9.7). DatastoreKit's call; SI's plan is corrected to
match.

**The release.** CI green at both tested ends, then the tag pushed, as for `v0.4.0` (the
`fingerprint` campaign, prompt 02).

## 5. What each client does with it

- **SI**, in a pin prompt of its own after its migration campaign's prompt 11 (or folded into its
  close, prompt 12, if the user rules so), and before it adopts RunRegistryKit:
  - pins the release (one line of `requirements.txt`, installed as its prompt 08 did);
  - adds `GradientCoupledInstantonValue` (`instanton_serial`) to `GradientCoupledInstanton`'s spec
    under the new field, beside the profile in `values`;
  - moves it from its coverage test's `EXCLUDED` to the tables read through an owner (naming the new
    slot), so that all 30 entries are covered and none excluded;
  - shows the count in `tools/inventory_report.py`;
  - closes `[gci-value-table-outside-the-inventory]`.
  Its prompts 11 and 12 do not wait for the release.
- **ChamPBH** and **SGK**: nothing. Each may stay on its pin; under the recommended design, their
  recorded fingerprints stay valid whether they move or not.

## 6. Rules that come with this request

- **No change in a client.** The campaign reads SI, ChamPBH and SGK through `git` only; it edits
  none of them.
- **Nothing the pool writes or reads changes**, and no message, refusal or exception of the pool's.
  The change is in `store_inventory.py` (and, if DatastoreKit decides so, a comment in
  `store_fingerprint.py`).
- **Nothing else rides in the release.** A defect found while doing this is recorded and opened on
  DatastoreKit's board, not fixed in this release, unless the user rules otherwise. In particular,
  `[00-the-inventory-cannot-see-a-serial-split]` (`docs/OPEN_ISSUES.md`) is not in scope.
- **Counts, not contents.** A fingerprint counts value rows and does not hash them, by design (SGK's
  brief, `:122-123`). The extra tables are counted in the same way; nothing here asks to hash them.

## 7. First steps

1. Re-measure §3's five points at DatastoreKit's `HEAD`.
2. Read `store_inventory.py` (`InventorySpec`, `Record`, `read_records`, `_combine`,
   `inventory_classes`), `store_fingerprint.py`'s `ENCODING_FORMAT` comment, contract §4 and §9.7,
   and the `fingerprint` campaign's README §1 (its out-of-scope list).
3. Decide the design and the `ENCODING_FORMAT` question, and record both as decisions.
4. Plan the campaign under DatastoreKit's conventions: decisions recorded, one commit per prompt, the
   tag made by a prompt that says so.
5. When the release is tagged, tell the user the tag object and commit. SI's pin prompt is written
   from them.
