# Campaign — dk-and-rpk-migration

**Written:** 2026-10-11 on `main` at `7bb3efd`, by Claude Opus 5.5. **Status: reviewed; prompts
01–04 and 01a written (2026-10-12); 01 and 01a landed; 02's first attempt stopped (2026-10-20).**
All eleven decisions of §6.1 are ruled: U3, U8 and U9 on their own, and U1, U2 and U4–U7 as
recommended, on 2026-10-12; U10 on 2026-10-19; U11 on 2026-10-20.
P1–P19 stand as proposed (§6.2). The DatastoreKit release U3 asked for is out, as `v0.3.0` (§0.4),
and is carried unchanged into `v0.4.0`, which the campaign pins (U10; §0.5).

*Revised 2026-10-12, when the user ruled U3: the row's timestamp goes into DatastoreKit's
`DatastoreObject`, in a release requested by
[`datastorekit-v0.2.4-brief.md`](datastorekit-v0.2.4-brief.md), not into a class of SI's own. 06
loses its timestamp half, and 08 pins that release in place of `v0.2.3`.*

*Revised 2026-10-12 again, when DatastoreKit released it as **`v0.3.0`** (tag object `bf0a3b2`,
commit `2f5417e`), a minor release since it adds to the API. The brief keeps its name, as the
record of the request; the plan pins `v0.3.0` (§0.4).*

*Revised 2026-10-12 a third time, after 01's review, when the user ruled **U9**: SI's rehearsal
cluster is isolated from other projects' (its own temp dir and ports) and stops only itself, never
by `ray stop`, and a lock shared with ChamPBH and SecondaryGWKit lets one rehearsal run at a time
on this machine. The contract is [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md); a new
prompt, 01a, implements SI's side before 02. §2, §4, §4.1, §5 (rules 17–18) and §6.1 amended, and
prompt 02 with them.*

*Revised 2026-10-19, when the user ruled **U10**: the campaign pins DatastoreKit **`v0.4.0`** (tag
object `8e7c1d7`, commit `c8570e8`, released 2026-10-14) in place of `v0.3.0`. `v0.4.0` adds one
module, `store_fingerprint.py`, which SI does not call, and carries `v0.3.0` unchanged; SI's
checklist addendum for it says nothing changes for SI. RunRegistryKit's `[stores]` extra requires
`datastorekit>=0.4.0`, so the later RunRegistryKit adoption needs no second pin. RayPoolKit has made
no release since `v0.2.0`, so 03 and 04 stand. §0, §0.5 (new), §2, §2.1, §2.2 (08), §4, §6.1, §6.3
and §7 amended. No prompt already written changes.*

*Revised 2026-10-20, when the user ruled **U11**: **no rehearsal builds the gradient branch.** 02's
first `reference` build ran 5 h 36 min and was stopped: its homogeneous branch was stored in about
35 s, but none of the four gradient solves of the first wave finished, each running over five
hours with every inner Picard step failing and the shooting halving λ again and again
(`[gci-picard-inner-fails-on-rehearsal-grid]`). July's 315 s a solve (§0.2) was measured at an
older tree. The dense builds become `--targets homogeneous`, the interrupt moves to
`STAGE 2: FULL MSR INSTANTONS`, and the readers no longer run `plot_GradientCoupledSolutions.py`.
The gradient tables are left to the suites (§1). §0.2, §1, §4.1, §4.3, §6.1 (U11) and §6.2 (P1)
amended, with prompt 02, `build.sh` and `run_readers.sh`.*

It is planned from:
- **the two packages' adoption checklists for StochasticInstantons (SI)**, which are data, not
  instructions:
  - DatastoreKit's `docs/adoption/stochasticinstantons.md`, read with its three addenda (`v0.2.1`,
    `v0.2.2`, `v0.2.3`), and its `docs/adoption/README.md` and `docs/client-contract.md`; and, as
    each release came, its `v0.3.0` addendum (§0.4) and its `v0.4.0` addendum (§0.5);
  - RayPoolKit's `docs/adoption/stochasticinstantons.md` and its `docs/adoption/README.md`.

  Both repositories are under `/Users/ds283/Documents/Code/`. **No prompt edits either** (§5
  rule 12).
- **the two sibling campaigns of the same name**, whose shape this one follows:
  - ChamPBH's `prompts/dk-and-rpk-migration/README.md` (CPBH). It is the closer model: CPBH's
    layer, like SI's, holds client data and registers factory instances.
  - SecondaryGWKit's `prompts/dk-and-rpk-migration/README.md` (SGK). SGK's layer was already
    generic, and SGK had a run registry and a store fingerprint, which SI does not.

  Where SI differs from CPBH, this plan says so (§0.1).

§0.2 re-measures both checklists at `7bb3efd`. §2 fixes each prompt's charter and acceptance.
§6.1 holds the seven decisions that are the user's; §6.2 holds the planner's proposals.

## 0. Why this campaign exists

SI's datastore layer (`Datastore/`, `ShardedPool`) and its Ray work queue
(`RayTools/RayWorkPool.py`) are copies of ChamPBH's. Each has now been extracted into a package of
its own:
- **DatastoreKit**, `datastorekit` **`v0.4.0`**: tag object `8e7c1d7`, on commit `c8570e8`,
  released on 2026-10-14 by DatastoreKit's `fingerprint` campaign (U10; §0.5). It adds a module SI
  does not call, and carries `v0.3.0` unchanged:
  - **`v0.3.0`**: tag object `bf0a3b2`, on commit `2f5417e`, released on 2026-10-12 at SI's request
    (U3; §0.4). Its `DatastoreObject` carries the row's timestamp.
  - It carries everything of `v0.2.3` (tag object `8dac562`, commit `0de2b16`, released on
    2026-10-11 at CPBH's request), whose factory base accepts SI's registry of instances.

  SI's checklist addendum for `v0.4.0` gives SI's pin as `v0.3.0` or `v0.4.0`, as SI chooses; U10
  chooses `v0.4.0`.
- **RayPoolKit**, `raypoolkit` **`v0.2.0`**: tag object `4e7eb15`, on commit `eaef0ce`. Still its
  latest release on 2026-10-19 (§0.5).

SGK, ChamPBH and SI will all depend on them. Each package names SI's adoption as its gate **G4**:
- **DatastoreKit's G4** (checklist item 9, as its `v0.3.0` and `v0.4.0` addenda amend it):
  - SI's 9 layer files are deleted, and SI imports `datastorekit` at `v0.3.0` or later (SI:
    `v0.4.0`, U10);
  - SI's non-integration and integration suites pass;
  - **a small grid is rebuilt through the package**. What it is compared against is SI's choice.
- **RayPoolKit's G4** (checklist item 8):
  - `RayTools/` is gone and nothing imports it, nor `_default_store_handler`;
  - the pin is installed and SI's suite passes;
  - all 16 `RayWorkPool(...)` sites construct.

Since RayPoolKit's decision U5 (2026-10-10), `RayTools/` may not be edited until SI adopts; a fix
to the pool is made in RayPoolKit. SI's copies are also on `CLAUDE.md`'s protected list
(`CLAUDE.md:89-112`), so every prompt that touches one names it and says exactly what changes.

### 0.1 Like ChamPBH, and where SI differs

**SI's layer is CPBH's, and so is most of its adoption.** DatastoreKit's checklist (its "In one
paragraph") puts it as: "SI's layer is 9 files, 2,679 lines, close to CPBH's." The CPBH items that
carry over:

1. **SI's own data lives inside the layer** (checklist item 4). It must leave before the layer can
   be deleted:
   - the factory registry `_factories`, 30 instances (`Datastore/SQL/Datastore.py:96-127`), with
     its imports (`:28-86`);
   - the five drop groups and their order (`:133-147`);
   - the serial batch sizes (`Datastore/SQL/ClientPool.py:24-54`).

   The package takes them as `ShardedPool(factories=…, serial_batch_sizes=…, drop_tables=…)`.
2. **The registry holds instances.** Under `v0.2.2` the 16 classes that define only `register` and
   `build` would raise `TypeError`. **`v0.2.3` removes this**, and SI's checklist addendum
   confirms it. This covers the 18 registry entries and the three instantiations at import
   (`CosmologyConcepts/Potentials/registry.py:33`, `:40`;
   `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:71`). SI's factories change only
   their base's import path.
3. **Shard keys in payloads.** The package takes only the mapping form, `{"delta_Nstar": key}`.
   SI has 15 `object_get_vectorized` calls that pass a bare key (`main.py` 10,
   `plot_InstantonSolutions.py` 3, `plotting/fetch.py` 2). SI's layer already accepts the mapping
   (`Datastore/SQL/ShardedPool.py:595-605`), so the change can land before the swap. **Unlike
   CPBH, one test stub fails on the mapping:** `tests/test_plot_adapters_golden.py:1010-1012` keys
   its canned responses by `(class_name, shard_key)`, and a dict is not hashable. That stub, and
   the three in `tests/test_plot_extraction_golden.py` (`:381`, `:450`, `:477`), are named by the
   prompt that converts the calls (05).
4. **The inventory interface.** `main.py --inventory` calls `pool.inventory(...)` through five
   helpers (`main.py:1230-1328`). It is driven by `config/sharding.py`'s `inventory_config` and by
   17 factory `inventory()` hooks. One integration test also calls it
   (`tests/test_grid_builder_integration.py:133-135`). The package has no `pool.inventory`. Its
   inventory is `datastorekit.store_inventory.read_inventory(primary, factories)`: read-only, on a
   closed store, over each factory's `inventory_spec()`.
5. **Drops.** The package takes tables, not groups, and refuses a drop that leaves references
   (checklist item 6):
   - `--drop full-instanton` or `--drop slow-roll-instanton` alone would leave `CompactionFunction`
     naming dropped rows;
   - `--drop inflaton-trajectory` reaches every sharded family. It also drops a replicated table,
     which is DatastoreKit's inherited issue
     `[00-a-drop-action-drops-a-replicated-table-outside-the-in-flight-record]`.
6. **Every SI store is refused by the package** (checklist item 8; decision U31: *rebuilt, not
   migrated*):
   - a read-write open stops first on the primary's missing `replication_in_flight`;
   - behind that are the absolute shard records, and the per-shard timestamps of replicated rows;
   - one recorded store also has a replicated serial split;
   - nine factory commits since June have changed columns.
7. **The harness.** `tests/conftest.py`'s `live_pool` (`:36-74`) builds SI's pool with
   `drop_actions=` and `inventory_config=` and without `factories=`. 61 integration tests in 11
   files reach it.

**What SI has that CPBH does not.** Each item below has a decision or a prompt of its own.

8. **`DatastoreObject.timestamp`** (checklist item 2). SI's `DatastoreObject` takes and exposes a
   row's `timestamp` (`Datastore/object.py:25-30`, `:43-45`); the package's takes `store_id` only.
   The usage:
   - 14 direct calls pass `timestamp=`, and 10 subclasses pass it through `super().__init__`;
   - three plot adapters read `.timestamp` directly (`plotting/adapters/full.py:61`,
     `gradient.py:133`, `slow_roll.py:66`);
   - the provenance footers read it by `getattr` (`plotting/provenance.py:41`,
     `plotting/figures/spatial.py:259`).

   **U3, ruled 2026-10-12:** the package gains it. The package already owns the column: it
   prepends it, stamps it (one stamp across shards for a replicated write), and reports it in the
   inventory. All three clients' factories write it: SGK in 19 files, CPBH in 16, SI in 21 of 22.
   Only the object's slot for the value is missing. With the release, SI's 24 sites work unchanged
   once their import is rewritten (09). The brief gives the evidence.
9. **`InflatonTrajectory` is a replicated class that validates and prunes at startup.** No CPBH
   class is. Four things follow (**U4**):
   - **The prune keyword.** The package calls a replicated class's `validate_on_startup` *by
     keyword*, `prune=` (`datastorekit/SQL/ShardedPool.py`, `_prune_needed` and `_prune_shard` at
     `v0.2.3`). SI's hook names the parameter `prune_unvalidated`
     (`Datastore/SQL/ObjectFactories/InflatonTrajectory.py:256`), so it must be renamed. The other
     11 hooks are called positionally and work as they stand.
   - **A latent SI bug, found in planning.** `InflatonTrajectory.validate_on_startup` deletes
     unvalidated trajectories and leaves their `InflatonTrajectoryValue` rows behind (`:256-266`).
     This is the orphaning that `.claude/rules/validate-on-startup.md` forbids, but that rule's
     cascade map omits the class. It is the same failure mode as that rule's recorded
     `SlowRollInstantonValue` incident: a reused trajectory serial meets its own orphans and
     raises a UNIQUE violation. It is opened on the board as
     `[inflaton-trajectory-prune-orphans-value-rows]`.
   - **The package's prune polices the unit.** It refuses a prune that deletes from any table
     outside the class's *unit*: the class, its tag tables, and the tables whose declared
     `owner_column` names it (`_unit_tables`, `_prune_shard`). So the cascade fix needs
     `InflatonTrajectoryValue` to declare `owner_column = "trajectory_serial"`, or the package
     refuses the prune. The two must land together.
   - **An interrupted replicated validate** is repaired at open only for a class that declares
     `validated_column` and defines `revalidate` (contract §2, §3). Otherwise the shards differ,
     and the next open is refused with `ReplicatedDivergence`. SI interrupts runs with Ctrl-C, so
     without the repair an unlucky interrupt would make the store unopenable.
10. **`_default_store_handler`.** `main.py:45` imports the pool's private name and passes it four
    times. What it passes is the default (RayPoolKit checklist item 3).
11. **References without a foreign key, and timings inside JSON.** These matter for comparing two
    stores by value (§4.2):
    - **four references are polymorphic, with no foreign key** (*corrected 2026-10-12, at 01's
      review: the plan first named two, and 01 found the other two*):
      - `potential_serial`, disambiguated by `potential_type`
        (`Datastore/SQL/ObjectFactories/InflatonTrajectory.py:53-63`);
      - `diffusion_serial`, disambiguated by `diffusion_type`, on three tables:
        `FullInstanton.py:78-79`, `SlowRollInstanton.py:77-78` and
        `GradientCoupledInstanton.py:91-92`.
    - **every compute target writes `compute_time` into `diagnostics_json`**, and
      `GradientCoupledInstanton` adds Picard timings. So two builds of one tree never agree
      byte for byte on those columns.
12. **SI's tests are pytest, and its integration tests need Ray.** SI's own convention allows this
    under the `integration` marker; CPBH's rule "no test needs Ray" is not SI's.
13. **Two version labels.**
    - `main.py` opens under `"2026.6.1"` (`main.py:49`).
    - The plot scripts open **read-write** under `plotting/provenance.py:18`'s `"2026.3.0"`. So
      each plot run adds a `version` row to the store it reads, under both layers alike, and the
      footers it draws say `v2026.3.0`.

    Out of scope here (P9); it is opened as `[plot-scripts-stale-version-label]`.

**What CPBH had and SI does not:**
- **no user pilot**, so the rehearsal grid is proposed (P1);
- **no run registry and no fingerprint**, so stores are compared by value (§4.2), as in CPBH;
- **no store that crosses the swap**, so the rehearsal before the swap and the one after it are
  compared through a tool that reads both formats and never goes through either layer.

### 0.2 Reconciliation against `7bb3efd`

Measured on 2026-10-11. The outputs are in [`measure/out/`](measure/out/).

**`7bb3efd` is `HEAD` of `main`, and it is both checklists' commit.** Both measuring scripts were
run from each package's root, with its own venv, at `--commit 7bb3efd`. Each equals its
checklist's appendix **byte for byte**:
- DatastoreKit's `docs/extraction/measure_client_imports.py si`
  ([`7bb3efd-datastorekit-measure_client_imports.md`](measure/out/7bb3efd-datastorekit-measure_client_imports.md)):
  - 48 import statements of the layer, in 47 files; 1 is nested (under `TYPE_CHECKING`);
  - 0 string literals and 0 `import_module` calls;
  - 2 factory imports outside the factory package.
- RayPoolKit's `docs/adoption/measure_client_pools.py si`
  ([`7bb3efd-raypoolkit-measure_client_pools.md`](measure/out/7bb3efd-raypoolkit-measure_client_pools.md)):
  - 3 imports of `RayTools`, one naming a private name;
  - 16 `RayWorkPool(...)` calls (12 with no compute handler, 4 with one), every one "constructs";
  - 5 flags on non-literal sizes, on 4 calls;
  - 0 test modules naming either.

So every figure the checklists give is today's. A prompt re-measures at its own `HEAD` before it
acts, and its numbers govern.

**The tags are on their remotes.** `git ls-remote --tags` gives:
- DatastoreKit: `refs/tags/v0.2.3` → `8dac562` (`^{}` `0de2b161ba09…`);
- RayPoolKit: `refs/tags/v0.2.0` → `4e7eb15` (`^{}` `eaef0ce60e2f…`).

**The venv.**
- Python 3.13.16: `venv/` links to MacPorts' 3.13 framework, and `venv/pyvenv.cfg` records 3.13.13,
  the version when the venv was made. `ray==2.55.1` and `SQLAlchemy==2.0.46`
  (`requirements.txt:57`, `:65`).
- **All three equal both packages' tested high end**, so unlike CPBH (Ray 2.53.0) SI runs each
  package at a tested configuration.
- `pip show datastorekit raypoolkit` finds neither, and `pip check` reports nothing broken.
  `pip freeze` (81 lines) is saved as [`7bb3efd-pip-freeze.txt`](measure/out/7bb3efd-pip-freeze.txt),
  for 03 and 08 to compare against.

**The suites at `7bb3efd`** ([`7bb3efd-suites.md`](measure/out/7bb3efd-suites.md)):

| Selection | Collected | Result |
|---|---|---|
| `-m "not integration and not slow"` | 631 of 761 | 630 passed, 1 skipped (110 s) |
| `-m "integration"` | 61 | 60 passed, 1 skipped (24 s; `live_pool` started its own local Ray) |
| `-m "slow and not integration"` | 69 | not run at planning; 02 measures it |

`CLAUDE.md:21` and `.claude/rules/test-selection.md:10`, `:26` still say "464 of 571". This is
opened as `[test-counts-stale-in-claude-md]`, and 12 corrects it.

**Formatting.** `black` is not installed. `ruff format --check .` would reformat 116 of 195 files,
`main.py`, `Datastore/SQL/Datastore.py` and `plotting/fetch.py` among them, and `ruff` is not
pinned in `requirements.txt`. So no prompt asks for formatter-clean files. A touched file keeps its
formatting (§5 rule 15).

**Things read at planning that the charters rely on:**
- **The old layer ignores `register()` keys it does not read** (`Datastore/SQL/Datastore.py:297-330`).
  It calls `validate_on_startup` **positionally** (`:443-446`) and never calls `revalidate`. So
  U4's factory changes are inert on the old layer, except the cascade, which is the bug fix. They
  can therefore land before the swap and be rehearsed (06, 07).
- **Every replicated get-or-insert `build` sets `_new_insert`** on an insert (e.g.
  `delta_Nstar.py:49`, `efold.py:47`, `tolerance.py:56`). The package copies a replicated get to
  the other shards only when that is set (contract §6), so SI's replicated gets will cross.
- **`InflatonTrajectory.store` already threads the controller's serial** through to the other
  shards (`InflatonTrajectory.py:186-200`), which is what the package's replicated store expects.
- **The rehearsal's gradient solves are bounded, and do not depend on the clock.** At
  `m = 10⁻⁵ M_P`, `n = 5`, `δN★ = 1.0`, a `GradientCoupledInstanton` took 315 s in July and stopped
  at its cap of 50 outer iterations (`.documents/gradient-coupled-instanton/24-phase-a-deep-dive.md:43`).
  That is a stop set by an iteration count, not by a wall-clock budget. It seeds from a
  `FullInstanton` fetched from the store, and the homogeneous branch finishes before the gradient
  branch starts (`main.py:1114`, `:1127`). So the seed is the same in a straight-through build and
  in a resumed one. §4.3 measures whether the builds agree rather than assuming it.
  *Corrected 2026-10-20 (U11): at 02's tree no solve of the rehearsal grid finished in over five
  hours, every inner Picard step failing. July's figure does not hold, and no rehearsal builds
  the gradient branch.*
- **One combination of flags crashes at the start tree:** `--no-store-values` with
  `--targets homogeneous gradient` (`[gci-main-no-store-values-crash]`, `.documents/OPEN-ISSUES.md`
  §3; seen in Phase A, `24-phase-a-deep-dive.md:27-33`). The rehearsal avoids it (§4.1), and this
  campaign does not fix it (§5 rule 4).

**The stores.** None is opened by this campaign except its own rehearsal stores (§3). They are
named only:
- in the working tree (ignored):
  - `out-gci-convergence-campaign/phase_a.sqlite` and `phase_a_followup.sqlite`, with their
    shards. The July close-out keeps them "as the primary evidence for the results table";
  - `test-gradient.sqlite`, with `test-gradient-profile.sqlite` and ten shards;
- in SI's notes: the June stores (`SMSR_scaling*.sqlite`, `large-grid-1500.sqlite`,
  `doe-run-500.sqlite`, `quad-ast-small-*.sqlite`), whose `S_MSR` numbers are all provisional
  (`[june-smsr-results-provisional]`).

**No run is live.** No Ray cluster is up (`ray status` finds none).

### 0.3 Where this campaign sits in SI's plan

`.prompts/INDEX.md` plans **P2** (`fullinstanton-hamiltonian`, which re-runs the June grids) and
then **P3** (`onion-rebuild`). DatastoreKit's checklist advises adopting at the start of P2, and
tagging the last commit on the old layer first (item 8, "Advice (U31)").

This plan proposes that **the migration runs before P2** (U7):
- P2's grids are then built through the packages from the start;
- P2's first prompt, `[hfp-closed-form-audit-not-run]`, reads the June and July stores. It runs at
  a tag on the old layer (07 creates it), from a worktree that uses the main checkout's venv. The
  two packages installed there are inert to a tree that does not import them.

So SI, unlike CPBH, owes **no science-store rebuild** to this campaign. Every June `S_MSR` number
is to be recomputed by P2 anyway, and the July `phase_a` stores stay readable at the tag.

### 0.4 DatastoreKit `v0.3.0`, as delivered (2026-10-12)

Released by DatastoreKit's `object-timestamp` campaign (closed at `5f972be`), from
[`datastorekit-v0.2.4-brief.md`](datastorekit-v0.2.4-brief.md).
- **The tag.** `git ls-remote` gives `refs/tags/v0.3.0` → `bf0a3b25afa5…`, `^{}` →
  `2f5417ea76cd…`. The pin was `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.3.0`,
  until U10 moved it to `v0.4.0` (§0.5).
- **What changed in the package since `v0.2.3`**, by `git diff --stat v0.2.3 v0.3.0 --
  datastorekit pyproject.toml`: `datastorekit/object.py` (19 lines), the version, and tests. No
  other layer file changed. Read through `git show`, `DatastoreObject.__init__(self, store_id, *,
  timestamp=None)` takes a **keyword-only** `timestamp`, and `timestamp` is a read-only property
  whose docstring says the layer neither sets nor reads it. 08 checks this on the installed
  package.
- **What SI's checklist addendum says** (`docs/adoption/stochasticinstantons.md`, "Addendum:
  v0.3.0"), measured by an `ast` read of SI at `7bb3efd`:
  - of SI's 23 `DatastoreObject.__init__(…)` calls, 9 pass `store_id` alone and 14 pass
    `timestamp=` by keyword;
  - the 10 pass-throughs pass it by keyword too;
  - so all 24 timestamp sites work as they stand once their import is rewritten.

  A positional timestamp would be refused, and SI passes none.
- **Five points the implementing agent relayed**, none of which changes a charter here:
  1. One DatastoreKit test compared `vars()` of the package's version object, and gained the
     `_timestamp` key, so the brief's test 4 could not hold for it as written. **No SI file calls
     `vars(` or reads a `__dict__`** (the addendum).
  2. The package has 18 positional `DatastoreObject.__init__` calls and SI 12 test stand-ins, more
     than the brief listed. The brief's conclusions hold.
  3. The version is `v0.3.0`, not `v0.2.4`: it adds API, so it is a minor release by DatastoreKit's
     rules.
  4. `timestamp` is keyword-only. All 24 SI sites pass it by keyword.
  5. A sixth `def timestamp`, at `tests/test_plot_adapters_golden.py:870`, is on a stand-in, not a
     `DatastoreObject`, and is unaffected.
- **Nothing else rides in it.** DatastoreKit's `inherited-issues` board (opened 2026-10-12, no
  prompts) now holds `[00-a-drop-action-drops-a-replicated-table-outside-the-in-flight-record]`,
  cited in §0.1 item 5. Its state is unchanged by `v0.3.0`.

### 0.5 DatastoreKit `v0.4.0`, and RayPoolKit, as of 2026-10-19

Checked on 2026-10-19, read-only, in both repositories (each at its remote `main`: DatastoreKit
`38ebb9f`, RayPoolKit `17029d9`).
- **The tag.** `git ls-remote` gives `refs/tags/v0.4.0` → `8e7c1d77b379…`, `^{}` →
  `c8570e849334…`. Released on 2026-10-14 by DatastoreKit's `fingerprint` campaign (closed at
  `b01737f`). The pin is `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0`.
- **What changed in the package since `v0.3.0`**, by `git diff --stat v0.3.0 v0.4.0 -- datastorekit
  pyproject.toml`:
  - one new module, `datastorekit/store_fingerprint.py` (351 lines): `fingerprint_of`,
    `compare_fingerprints`, `listing_lines` and `ENCODING_FORMAT = 1`, pure functions over what
    `read_inventory` returns (contract §9.7);
  - its tests, `datastorekit/tests/test_store_fingerprint.py`, and one golden data file under
    `datastorekit/tests/data/`;
  - the version line of `pyproject.toml`. `requires-python` and the dependencies are unchanged.

  `datastorekit/object.py` (U3, §0.4) and `datastorekit/store_inventory.py` (which 10 builds on)
  are unchanged. The layer never calls the new module, so nothing it writes, reads, refuses or
  raises changes.
- **What SI's checklist addendum says** (`docs/adoption/stochasticinstantons.md`, "Addendum:
  v0.4.0", read through `git` at SI's `5fb4a1d`): **"Nothing changes for SI."**
  - SI defines and calls none of the three functions, and no file names
    `datastorekit.store_fingerprint`;
  - the `v0.3.0` addendum's account of `DatastoreObject.timestamp` holds at `v0.4.0`, so SI's 24
    timestamp sites still change only an import (09);
  - SI's pin is `v0.3.0` or `v0.4.0`, as SI chooses, and **G4 reads "SI has adopted `v0.3.0` or
    later"** (`fingerprint` decision U6).
- **Why `v0.4.0` (U10).** RunRegistryKit's `[stores]` extra requires `datastorekit>=0.4.0`
  (RunRegistryKit `pyproject.toml`). RunRegistryKit now has an SI checklist
  (`docs/adoption/stochasticinstantons.md`, and `docs/adoption/v0.2.0/stochasticinstantons.md`):
  SI adopts its store layer only after this campaign, with a `datastorekit` of `v0.4.0` or later
  and 10's specs (§7). Pinning `v0.3.0` would leave a second pin commit for that campaign, for no
  gain: the layer SI runs is the same in both.
- **The other clients.** SGK adopted `v0.4.0` by its `runregistry-extraction` campaign, whose R1
  took the fingerprint both ways on four stores with no difference (DatastoreKit `38ebb9f`). CPBH
  stays on `v0.3.0`.
- **RayPoolKit has made no release since `v0.2.0`.** Its remote has the tags `v0.1.0` and `v0.2.0`
  only. `git diff --stat v0.2.0 17029d9` touches no file under `raypoolkit/` and not
  `pyproject.toml`: only documents and records (the adoption checklists, the verification, the
  G2 and G3 records). Its SI checklist was last changed on 2026-10-10 (`67f3f7e`), before this plan
  was written. So 03 and 04 stand as written.
- **Nothing else rides in it.** DatastoreKit's fingerprint plan defers "a second value table per
  spec" until SI's 10 settles it and the user asks (its README §1, out of scope); this plan's §6.3
  already leaves that to the user at 10.

## 1. Scope

**In scope:**
- run provenance in the drivers' output, the comparison tool and the rehearsal tooling (01);
- the three rehearsals RH0, RH1 and RH2, and their verification document (02, 07, 11). They are
  named RH to keep them apart from SI's calculation review "R1" (`notes/reviews/`);
- `requirements.txt`: the two pins (03, 08);
- `RayTools/`, deleted; its 3 imports rewritten; `_default_store_handler` dropped (04);
- SI's data moved out of the layer into `config/datastore.py`, and the 15 vectorized gets put in
  the mapping form, with the four test stubs that mirror them (05);
- `InflatonTrajectory`'s factories made fit for the package's replicated protocol, with the
  orphan fix (U4) (06);
- the brief for the DatastoreKit release that carries the timestamp (U3). The release itself is
  DatastoreKit's work, not this campaign's;
- the 9 layer files (two `__init__.py` kept, emptied, P6) and every layer import outside
  `.prompts/` rewritten by the module map. With them go the four pool constructions, the drop
  policy (U5) and the `live_pool` harness (09);
- the inventory: `inventory_spec()` on the factories, an SI report over `read_inventory`, and
  `main.py --inventory` on a closed store (10);
- prose that a prompt's own commit makes false (P13), and at the close the documents, `CLAUDE.md`,
  the `.claude/rules/` files and the handover (12).

**Out of scope:**
- **What the code computes.** No stored science value may change (§5 rule 9). The orphan fix
  changes which rows a prune deletes, not any value. `VERSION_LABEL` stays `2026.6.1` (P9).
- **DatastoreKit and RayPoolKit themselves** (§5 rule 12). A defect found in either stops the
  prompt (§5 rule 11). The release U3 asks for is made in DatastoreKit, from the brief, by no
  prompt here.
- **The factories' form.** They stay instances whose hooks take `self`. They gain only what U4 and
  10 add.
- **Migrating stores** (U31: rebuilt, not migrated). No converter is written. The June and July
  stores are read at the tag (U7) and are not rebuilt by this campaign.
- **The plot scripts' version label and read-write pools** (P9, P10).
- **`redshift`**, a ChamPBH leftover. It is registered (`Datastore/SQL/Datastore.py:99`) but is in
  neither table list and is used by nothing. It stays registered (P12) and is opened as an issue.
- **`.prompts/`** (its layer and `RayTools` lines are history), **`.documents/` records that are
  dated**, and the July/June results.
- **The gradient-coupled code's science.** It is halted, and P3 replaces it. Its tables are
  exercised here only as tables, and only by the suites: its solves do not converge on the
  rehearsal grid, so no rehearsal builds them (U11).

## 2. Prompts

| # | Prompt | Covers | Model |
|---|---|---|---|
| 01 | `01-rehearsal-tooling-and-run-provenance.md` | P5: each driver prints the installed `datastorekit` and `raypoolkit`. `tools/compare_stores.py` (§4.2), with its tests. The rehearsal scripts (§4.1) | Opus |
| 01a | `01a-isolate-the-rehearsal-cluster.md` | **U9.** `ray_cluster.sh start\|stop\|status`: SI's cluster on its own temp dir and ports, stopped by a targeted stop, never `ray stop`, under the shared rehearsal lock ([`rehearsal-lock-brief.md`](rehearsal-lock-brief.md)). Proved on a real cluster beside a decoy, with no build | Sonnet |
| 02 | `02-rehearse-the-start-tree.md` | **RH0.** §4.1 at 01's tree. It measures whether two builds of one tree agree bit for bit, which sets RH1's and RH2's criterion (§4.3). It also measures the `slow` block once, for 09 | Opus |
| 03 | `03-pin-raypoolkit-v0.2.0.md` | The `raypoolkit` pin in a commit of its own, installed; one distribution added | Sonnet |
| 04 | `04-adopt-raypoolkit.md` | **The RayPoolKit swap.** `RayTools/` goes; 3 imports rewritten; `_default_store_handler` dropped (7 lines). **RayPoolKit's G4 holds** by its checklist | Sonnet |
| 05 | `05-move-si-data-out-of-the-layer.md` | `config/datastore.py` holds the registry, the drop groups and the serial batch sizes, and the old layer reads them from there. The 15 vectorized gets take `{"delta_Nstar": key}` (P8), and the four named test stubs follow. On the old layer; the schema does not change | Sonnet |
| 06 | `06-prepare-the-inflaton-trajectory-factories.md` | U4: `InflatonTrajectory`'s cascade (the orphan fix), the `prune` keyword (all 12 hooks), `owner_column`, `validated_column` and `revalidate`. On the old layer; the schema does not change | Opus |
| 07 | `07-rehearse-before-the-datastore-swap.md` | **RH1.** §4.1 at 06's tree: `raypoolkit`, the data move and the preparation, on SI's layer. Equal to RH0. **Tags the last commit on the old layer** (U7) | Opus |
| 08 | `08-pin-datastorekit-v0.4.0.md` | The `v0.4.0` pin (U10; §0.5), which carries `v0.3.0`'s timestamp (U3; §0.4), in a commit of its own, installed as 03. On the installed package, SI's factory classes instantiate on its base, and its `DatastoreObject` carries a timestamp | Sonnet |
| 09 | `09-adopt-datastorekit.md` | **The DatastoreKit swap.** The 7 layer modules go and the 2 `__init__.py` are emptied (P6). Every layer import outside `.prompts/` is rewritten. The pools take `factories=`, `serial_batch_sizes=` and `drop_tables=`. U5's drop refusal. `live_pool` is rebuilt. `--inventory` refuses until 10 (P11) | Opus |
| 10 | `10-port-the-inventory.md` | `inventory_spec()` on the factories. `tools/inventory_report.py` over `read_inventory`. `main.py --inventory` on the closed store, before Ray. The 17 `inventory()` hooks and `inventory_config` deleted | Opus |
| 11 | `11-rehearse-through-both-packages.md` | **RH2.** §4.1 through both packages. Equal to RH1 by §4.2. **DatastoreKit's G4 holds** | Opus |
| 12 | `12-close-the-migration.md` | `CLAUDE.md` (the protected list, the test commands and counts), the `.claude/rules/` files, the documents. The final measurements. The G4 records drafted for both packages' boards. The handover to P2. The index; the board closed | Sonnet |

### 2.1 When each prompt file is written

Every charter below is fixed by a checklist, by a decision of §6.1, or by §4, so no prompt waits
on another's *scope*. The files are still written in batches, each just before its dispatch, so
that each carries the previous review's findings:
- **01–04** are written first, once the user has reviewed this plan and ruled on U1–U7 and
  P1–P19. *Written 2026-10-12.*
- **01a** follows 01's review and the ruling U9. *Written 2026-10-12.* 02 waits on it.
- **05–07** follow 02's review. RH0's reproducibility (§4.3) fixes 07's criterion.
- **08–11** follow 07's review. 07's results note fixes the counts and names they cite. The
  release U3 asked for is tagged (`v0.3.0`, §0.4), and so is the release 08 pins (`v0.4.0`, §0.5;
  U10), so 08 waits on nothing else.
- **12** follows 11's review.

Orchestrator notes are written one prompt at a time, in [`orchestrator/`](orchestrator/), just
before each dispatch.

### 2.2 The charters

**01 — Rehearsal tooling and run provenance** (Opus).
- **What it adds.**
  - **P5, provenance.** A helper `installed_package_provenance(names) -> dict`, in
    `utilities.py`. That file is on the protected list, and this prompt names it; it adds two
    functions and changes nothing else. CPBH's helper of the same name landed at ChamPBH
    `d7791c5`, and is 01's model.
    - For each distribution it gives `None` if the distribution is not installed. Otherwise it
      gives `{"version", "url", "commit", "requested_revision", "editable"}`, read from
      `importlib.metadata` and its PEP 610 `direct_url.json`, with `None` for any field the
      install does not record.
    - It has the shape of SGK's `RunRegistry.package_provenance()` and of CPBH's helper, so that
      a later move to a shared registry is a substitution.
    - `main.py`, `plot_InstantonSolutions.py` and `plot_GradientCoupledSolutions.py` each print one
      line from it, for `datastorekit` and `raypoolkit`, before they open a pool. It never refuses,
      even for an editable install.
  - **`tools/compare_stores.py`**: §4.2's comparison, and its schema snapshot. Its tests are in
    `tests/test_compare_stores.py`, on temporary SQLite files built by `sqlite3` alone. It is
    modelled on CPBH's tool of the same name, which landed at ChamPBH `d7791c5` (read there, not
    imported).
  - **The rehearsal scripts** under `.documents/dk-and-rpk-migration/rehearsal/` (§4.1):
    - `build.sh`: one build, given the store, the slug, the mode (dense or scalars-only) and
      whether it resumes;
    - `interrupt_when.py`: sends `SIGTERM` to a driver once its log shows a stage banner and a
      stated delay has passed;
    - `stage_counts.py`: each stage's queue-summary counts from a log, without the rates;
    - `run_readers.sh`: §4.1's L3.
- **Acceptance.**
  1. **The provenance tests** use stand-in distributions and no real install. They cover four
     cases: not installed; a VCS install at a tag; an editable install; a `direct_url.json` that
     is absent or unreadable. In today's venv both entries print as not installed.
  2. **The comparison's tests** cover:
     - two equal stores: an empty diff, exit 0;
     - a float changed in its last bit: named, exit 1;
     - a row present in one store only: named;
     - serials and shard assignment that differ while content is equal: an empty diff;
     - a bookkeeping column that differs: reported, not counted;
     - **a polymorphic reference resolved through its type column**, and the same row under two
       potential serials: an empty diff;
     - **a `diagnostics_json` whose `compute_time` differs**: an empty diff, the key reported. One
       whose science key differs: named;
     - a primary with absolute shard records, and one with bare names: both read;
     - no file it reads changes: checksums before and after.
  3. **The tool's type maps are tested** against `CosmologyConcepts/Potentials/registry.py`'s and
     `InflationConcepts/DiffusionModel/registry.py`'s. The test may import those modules; the tool
     may not.
  4. Each script runs with `--help`. No script is run on a real build yet.
  5. **Suites:** the default run gives 631 plus the new tests, all passing; `integration` gives
     61.
- **Out.** Any run of `main.py` on a store (02 does that).

**01a — Isolate the rehearsal cluster** (Sonnet; added for U9).
- **What it adds.** `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`: `start` takes the
  shared lock and starts SI's cluster on `/tmp/ray-si` and its own ports; `stop` stops it by a
  targeted stop and releases the lock; `status` reports both. The contract is
  [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md) §2–§3, shared with ChamPBH and SGK.
- **Acceptance.** A real start and stop, with no build: a second acquire refused; a decoy cluster
  on Ray's defaults left running by SI's stop; SI's actors listed by an invocation that reaches
  SI's cluster alone; a lock held by another project neither broken nor released. Three
  breakages. The suites unchanged.
- **Out.** Any build; any change to 01's scripts; ChamPBH and SGK, which carry out the brief
  themselves.

**02 — Rehearse the start tree, RH0** (Opus).
- **What it does.** Runs §4.1's protocol with slug prefix `dk-and-rpk-migration-02`, at 01's tree,
  on SI's layer and `RayTools/`. It also runs `pytest -m "slow and not integration"` once and
  records its count and duration, as the baseline for 09.
- **Acceptance.**
  1. §4.1's L1–L3 hold.
  2. Every driver's provenance line names both packages as not installed.
  3. **§4.3, measured.** `compare_stores` of `reference` against `resumed` is recorded in full.
     - If it is empty, RH0 is **bitwise reproducible**, and RH1 and RH2 are held to bitwise
       equality.
     - If it is not, the results note says which rows and columns differ and by how much, and the
       prompt stops for the user to rule on RH1's criterion before 05–07 are written.
  4. **L4's baseline is recorded:** each stage's counts, and what the resume recomputed and pruned.
  5. The schema snapshot of `reference` is saved, as the start tree's.
- **Its own stop condition.** A build that fails at the start tree, or an L1–L3 failure there, is
  SI's to fix, not this campaign's. The prompt stops and reports, and nothing after it is
  dispatched.
- **It creates** `.documents/dk-and-rpk-migration/verification.md` and adds its §1.

**03 — Pin `raypoolkit` `v0.2.0`** (Sonnet).
- **What it changes.** `requirements.txt` gains
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0`, in sorted position, and nothing
  else changes.
  - The venv is installed from it with `./venv/bin/pip install -r requirements.txt`, which needs
    the network.
  - Never `-e`, a local path, `--upgrade`, `--force-reinstall` or `--no-deps`.
- **Acceptance.**
  1. `pip freeze` differs from `7bb3efd-pip-freeze.txt` by exactly one added line, `raypoolkit` at
     `eaef0ce6…`; `pip check` is clean.
  2. `installed_package_provenance()["raypoolkit"]` gives:
     - `0.2.0`, commit `eaef0ce6…`, requested revision `v0.2.0`, `editable: false`;
     - and `["datastorekit"]` is `None`.
  3. The installed `raypoolkit/` equals `git -C <RayPoolKit> archive v0.2.0 raypoolkit`, file by
     file, less any test package.
  4. The default and integration runs give 01's counts. Nothing imports the package yet.
- **Rollback** is the revert plus `./venv/bin/pip uninstall -y raypoolkit`.

**04 — Adopt `raypoolkit`** (Sonnet). It names `RayTools/` (protected) and deletes it.
- **What it changes.**
  1. It deletes `RayTools/RayWorkPool.py` and `RayTools/__init__.py`. `utilities.format_time`
     stays SI's.
  2. It rewrites the 3 imports (`main.py:45`, `plot_GradientCoupledSolutions.py:100`,
     `plot_InstantonSolutions.py:72`) to `from raypoolkit import RayWorkPool`.
     - With them goes `RayTools/RayWorkPool.py:23`'s `from Datastore.SQL.ShardedPool import
       ShardedPool`, so DatastoreKit's rewrite list loses one line, and no U12 exception is
       needed.
  3. **It drops `_default_store_handler`** (RayPoolKit checklist item 3, option (a)):
     - `main.py:1097` is deleted;
     - `_run_instanton_queue` stops taking `store_handler` (`:410`) and passing it (`:497`);
     - its three callers stop passing it (`:664`, `:824`, `:848`).

     The default is the same `obj.store()`.
  4. **It changes no other pool site** (P7). The 12 lookup-only sites keep
     `store_handler=None, persist_handler=None`.
  5. **The prose this commit makes false** (P13), as the checklist's item 9 advice lists it:
     - `CLAUDE.md:95`, the `RayTools/` entry in the protected list;
     - `.claude/rules/ray-dispatch.md:99-106`, which names the copy's file and its line numbers;
     - `.documents/FILE_MAP.md:31`, `:287`;
     - `.documents/INFRASTRUCTURE.md:353`;
     - `.documents/architecture-summary.md:27-28`, `:321`.
- **Acceptance.**
  1. `git ls-tree HEAD RayTools` is empty.
  2. **By RayPoolKit's script, at the commit:**
     - 0 imports, 0 string literals and 0 `import_module` calls name `RayTools`;
     - no import of `_default_store_handler`;
     - 16 calls, every one "constructs", with the flags of §0.2 checked by hand as the checklist's
       item 4 does.
  3. The default and integration runs give 03's counts.
  4. The three drivers byte-compile, and each module they import resolves, by `ast` (none is
     executed).
  5. **The deliberate breakages of §5 rule 8 are caught.** At least:
     - one import reverted to `RayTools.RayWorkPool`: the script reports it, and the import fails;
     - `raypoolkit` uninstalled: the import check fails.
  6. **The board records RayPoolKit's G4 as holding**, by its checklist item 8, items 1–5. RH1
     (07) adds the run under real Ray.

**05 — Move SI's data out of the layer** (Sonnet). On SI's own layer. It names
`Datastore/SQL/Datastore.py` and `Datastore/SQL/ClientPool.py` (protected) and says exactly what
changes in each.
- **What it changes.**
  1. **A new `config/datastore.py`** holds three objects, each moved verbatim with its imports:
     - `factories`: the registry `_factories`, 30 entries, each an instance, as today;
     - `drop_groups`: `_drop_actions`'s five groups;
     - `serial_batch_sizes`: `_default_serial_batch_size`, `temperature` and `redshift` included
       (P12).

     This is SGK's and CPBH's module name for the same data.
  2. **The old layer imports them from there:** `Datastore.py` its registry and drop groups,
     `ClientPool.py` its batch sizes.
     - `_drop_order` stays in the layer, which 09 deletes, since the package orders a drop by
       foreign key.
     - SI's fallback of 5 for a table the sizes do not name stays in the layer too (§0.1 item 1;
       the package's is 500). 05 records which registered tables lease serials and are not
       named. Expected: none but `version`, which leases none.
  3. **The 15 vectorized gets pass a mapping**, built by a one-line helper in `config/sharding.py`
     (P8), `vectorized_shard_key(key) -> {"delta_Nstar": key}`. Nothing else in their calls
     changes.
  4. **The four test stubs** take the mapping, and their assertions follow:
     `tests/test_plot_adapters_golden.py:1010` (keyed by the shard key) and
     `tests/test_plot_extraction_golden.py:381`, `:450`, `:477`. This is a named exception to
     §5 rule 7.
- **Acceptance.**
  1. **The schema does not change.** A temporary store built by the old pool at 05's tree has the
     schema snapshot of RH0's `reference`, table by table.
  2. **New tests:**
     - `config.datastore`'s three objects equal what the layer held at 04's tree, captured as data
       (the registry by name, class and constructor argument);
     - an `ast` test that every `object_get_vectorized` call outside the tests passes the helper's
       mapping (P8).
  3. The default and integration runs give 04's counts plus the new tests.
  4. **Deliberate breakages caught:**
     - one vectorized get reverted to the bare key;
     - a batch size changed;
     - a registry entry given another quantity type.

**06 — Prepare the `InflatonTrajectory` factories for the package** (Opus). On SI's own layer.
It touches no protected file. (Before U3 was ruled, this prompt also moved the timestamp onto a
class of SI's own; that half is now the DatastoreKit release's, §6.1.)
- **What it changes (U4).**
  - **The cascade.** `InflatonTrajectory`'s `validate_on_startup` deletes the unvalidated
    trajectories' `InflatonTrajectoryValue` rows before the trajectories, by `trajectory_serial`,
    as `.claude/rules/validate-on-startup.md` requires. The rule's cascade map gains its row. This
    closes `[inflaton-trajectory-prune-orphans-value-rows]`.
  - **`prune`.** The parameter is renamed from `prune_unvalidated` to `prune` in all 12 hooks that
    take it (P17), and in the rule's example. Each body changes only that name.
  - **`register()` gains two keys:**
    - `InflatonTrajectoryValue` declares `owner_column: "trajectory_serial"`;
    - `InflatonTrajectory` declares `validated_column: "validated"`.
  - **`InflatonTrajectory` gains `revalidate(serial, conn, table, tables)`.** It recomputes the
    stored row's flag by `validate`'s rule, writes it and returns it. The rule, as stored:
    - a row with `N_end` NULL is a failure, and is validated;
    - otherwise the row is validated when it has at least one value row.

    `store` writes the row and all its value rows in one transaction, so on any shard that holds
    the row, "at least one" and "all" coincide. The prompt checks this against `store` and
    `validate` and says so in its results note.
- **Acceptance.**
  1. **The schema does not change.** The temporary store's schema snapshot equals 05's. The two
     new keys are read by nothing on the old layer.
  2. **New tests, without Ray**, on a temporary SQLite store whose tables are built from the
     factories' `register()`:
     - the prune deletes a trajectory's value rows with it, and leaves another trajectory's;
     - `revalidate` agrees with `validate` on a complete row, a failed row, and a row whose value
       rows were removed by hand.
  3. **An integration test** through `live_pool`: a trajectory stored, its validation withheld,
     and a reopen with `prune_unvalidated=True` leaving no orphan. If `live_pool`'s session scope
     makes the reopen impossible, the test opens its own pool after `live_pool`'s module and says
     why.
  4. **Suites:** default and integration as 05 plus the new tests. The 12 hooks are all in
     `Datastore/SQL/ObjectFactories/`, so the diff touches no path of
     `.claude/rules/test-selection.md`'s list, and `slow` is not run.
  5. **Deliberate breakages caught:**
     - the cascade removed: the orphan test fails;
     - `revalidate`'s failure branch inverted.

**07 — Rehearse before the DatastoreKit swap, RH1** (Opus).
- **What it does.** Runs §4.1's protocol with slug prefix `dk-and-rpk-migration-07`, at 06's tree:
  `raypoolkit`, the data move and the preparation, on SI's layer.
- **Acceptance.**
  1. L1–L3 hold.
  2. Every provenance line names `raypoolkit` at `eaef0ce6…`, `editable: false`, and
     `datastorekit` as not installed.
  3. **Against RH0, by §4.2 and §4.3:** each RH1 store equals RH0's store of the same mode.
  4. **L4 against RH0:** each stage's counts, and what the resume recomputed and pruned, are RH0's.
     The queue banner, progress and summary lines keep their layout (RayPoolKit: "printed lines
     are part of the interface"). The rehearsal's interrupt falls after the trajectory stage, so
     no trajectory is pruned and 06's orphan fix makes no difference here; 06's tests and 09's
     acceptance 4 cover it.
  5. **U7, the tag.** Once 1–4 hold, an annotated tag `pre-datastorekit` is made on 07's commit:
     the last commit on SI's own layer, rehearsed. The user pushes it.
- **If RH1 misses,** the change is in 03–06, all on SI's layer. The prompt stops and records the
  diff.

**08 — Pin `datastorekit` `v0.4.0`** (Sonnet; *retargeted from `v0.3.0` on 2026-10-19, U10*). As
03, for `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0` (§0.5). It reads SI's
checklist addenda for `v0.3.0` and `v0.4.0`, and re-checks the tag on the remote before installing.
- **Acceptance.**
  1. `pip freeze` differs from 03's by exactly one line, `datastorekit` at
     `c8570e849334…`; `pip check` is clean.
  2. Provenance gives `0.4.0`, commit `c8570e849334…`, requested revision `v0.4.0`,
     `editable: false`.
  3. The installed `datastorekit/` equals `git archive v0.4.0 datastorekit`, less
     `datastorekit/tests` (adoption README §3), which at `v0.4.0` also holds the fingerprint's
     golden data file. It includes `datastorekit/store_fingerprint.py`, which nothing in SI's tree
     imports (§0.5).
  4. **What SI needs of the release, checked on the installed package** without touching SI's
     tree. A throwaway script, outside the repository:
     - **U3** (`v0.3.0`'s change, carried unchanged into `v0.4.0`, §0.5):
       - constructs `datastorekit.DatastoreObject(1, timestamp=t)` and reads `t` back;
       - without the argument, `timestamp` is `None`;
       - assigning to it raises `AttributeError`;
       - passing it positionally raises `TypeError` (it is keyword-only, §0.4);
     - **the factory base (`v0.2.3`'s change, carried into `v0.3.0` and `v0.4.0`):** defines a
       subclass of the installed `SQLAFactoryBase` with only `register` and `build` and
       instantiates it, and shows that one without `build` still raises `TypeError`.
  5. The default and integration runs give 06's counts.

**09 — Adopt `datastorekit`** (Opus). One commit, because the tree cannot pass between its parts.
It names every protected file it touches and says what changes in each: the layer files it
deletes, and the seven protected factories, the files of `MetadataConcepts/` and
`Quadrature/integration_metadata.py`, whose imports it rewrites.
- **What it changes.**
  1. **The files.**
     - It deletes the 7 layer modules: `Datastore/object.py`,
       `Datastore/SQL/{ClientPool,Datastore,ProfileAgent,SerialPoolBroker,ShardedPool}.py` and
       `Datastore/SQL/ObjectFactories/base.py`.
     - It replaces `Datastore/__init__.py` and `Datastore/SQL/__init__.py` with empty files (P6).
     - The factories stay.
  2. **The imports**, rewritten by the adoption README's §2 module map, module path only. 07's
     results note gives the count; it should be the checklist's 48 less the one 04 deletes,
     47 statements:
     - `SQLAFactoryBase` 24 (22 factories and the two registries; one under `TYPE_CHECKING`),
       to `datastorekit.SQL.factory_base`;
     - `DatastoreObject` 18: 12 from `Datastore` to `datastorekit`, and 6 from `Datastore.object`
       to `datastorekit.object`;
     - `ShardedPool` 4 (`main.py`, both plot scripts, `tests/conftest.py`);
     - `ProfileAgent` 1.

     **U3:** the 14 `DatastoreObject.__init__(…, timestamp=…)` calls and the 10 subclasses that
     pass `timestamp=` change nothing but their module's import. The package's `DatastoreObject`
     now takes the argument, keyword-only, and every SI site passes it by keyword (§0.4).
  3. **The factories change nothing but that import.** They stay instances; their hooks keep
     `self`.
  4. **The pools.**
     - The four constructions pass `factories=config.datastore.factories` and
       `serial_batch_sizes=config.datastore.serial_batch_sizes`.
     - `main.py`'s passes `drop_tables=`.
     - None passes `drop_actions=` or `inventory_config=`.
  5. **U5, the drop policy.** `main.py` turns `--drop` groups into tables. Before Ray starts, it
     computes each requested set's closure with `datastorekit.SQL.schema.dependent_tables`. If a
     group's dependents are not all requested, it refuses with a message naming the groups to
     add. For example, `full-instanton` alone gives "add `--drop compaction-function`". A test
     pins the message for each of the three unclosed groups, and acceptance for each closed set.
  6. **The harness.**
     - `live_pool` builds the package's pool with `factories=` and without the two retired
       arguments. Its 61 integration tests change only where an import does.
     - `tests/test_grid_builder_integration.py:133-135` counts rows by value without
       `pool.inventory`: through `pool.read_table`, or a `mode=ro` read of the temporary shard.
       This is a named exception to §5 rule 7, and the prompt records which it chose.
  7. **`--inventory`** prints that it is unavailable until 10 and exits non-zero, before Ray
     starts (P11). The five helpers and the four `pool.inventory` calls are deleted.
  8. **The prose this commit makes false** (P13):
     - `CLAUDE.md:89-112`: the protected list loses the layer's files;
     - `.claude/rules/pool-read-apis.md:8-15`, on `pool.inventory()`;
     - `.claude/rules/datastore-factories.md:245-301`: the account of replication, now the
       package's recorded write, checked at open;
     - `shard-key-assignment-bug.md` and `.claude/memory/bug-assign-shard-keys-key-id.md:24`: a
       status line saying the fix now lives in the package.
- **Acceptance.**
  1. **By DatastoreKit's script, at the commit:**
     - none of the 7 deleted modules is present, and the two `__init__.py` are present and 0
       bytes;
     - outside `.prompts/` there are 0 import statements, 0 string literals and 0 `import_module`
       calls naming a layer module.
  2. **The suites.** Default and integration give 08's counts, less any test deleted with a named
     reason, plus 09's new tests. The results note derives the counts by module. `slow` passes
     once, since the diff touches `ComputeTargets/`.
  3. **Without Ray:**
     - `config.datastore` imports, so all 30 registry entries are built on the package's base;
     - `python -m datastorekit.tools.sharded_store --help` exits 0;
     - the drivers byte-compile, and every module they import resolves (by `ast`; none is
       executed);
     - a temporary store built through the rebuilt harness has 06's schema snapshot, except for
       the columns the package orders differently (`serial`, `version`, `timestamp`, `stepping`;
       contract §2). Each difference is listed.
  4. **Under real Ray, at least once:** a 2-shard temporary store through the package, in which an
     unvalidated `InflatonTrajectory` and its value rows are pruned at open by the package's
     replicated prune (U4), on both shards, with no refusal. An integration test or a recorded
     verification step; the prompt says which.
  5. **U3, through the package:** an integration test through `live_pool` that a replicated object
     (a `delta_Nstar`) and a sharded one (a `FullInstanton`), each fetched back after it is stored,
     carry a timestamp that is not `None` and equals the row's `timestamp` column.
  6. **The deliberate breakages of §5 rule 8**, at least:
     - a factory's `SQLAFactoryBase` import pointed back at the deleted `base`;
     - a factory's `timestamp=row.timestamp` dropped from its `build`: acceptance 5's test fails;
     - `owner_column` removed: the package refuses the cascading prune;
     - the drop check removed: U5's test fails;
     - `factories=` dropped from `live_pool`.
- **Out.** The inventory (10). Any store but temporary ones; 09 runs no build.

**10 — Port the inventory** (Opus). It names the protected factories it adds a spec to.
- **What it changes.**
  1. **Each factory whose class the report covers defines `inventory_spec()`, and so does every
     class a spec depends on** (contract §4). That covers:
     - the parameters: `delta_Nstar`, `N_init`, `N_final`, `efold_value`, `n_collocation_points`,
       `alpha_regularization`;
     - the quantities: `phi_value`, `pi_value`, `inflaton_mass`, `quartic_coupling`;
     - the potentials, `MasslessDecoupledDiffusion`, `tolerance`, `CosmologicalParams`, `version`
       and `store_tag`;
     - the five compute targets, with their value tables.

     Some points are settled here and some are the prompt's:
     - The quantity factories' specs are instance methods, since their table is held on the
       instance. The package reads the spec by `getattr` on the registry entry.
     - **The four polymorphic references are `Parent(types=…, type_column=…)`**, with the type
       column among the leaves: `InflatonTrajectory`'s potential, and the diffusion model of
       `FullInstanton`, `SlowRollInstanton` and `GradientCoupledInstanton` (§0.1 item 11, as
       corrected at 01's review).
     - `GradientCoupledInstanton` has two child tables and a spec has one `values` slot. How the
       second is reported is the prompt's to settle, and record.
     - Which columns are leaves and which are parents the prompt derives from each `build`
       lookup, and records table by table.
  2. **A new `tools/inventory_report.py`**, `format_inventory_report(inventory, db_name, units,
     verbose=False)`. It renders a `StoreInventory` and reads nothing itself. It is modelled on
     SGK's (and CPBH's, if landed), read there and not imported.
     - It shows at least what today's `--inventory` shows (P18): each parameter's and quantity's
       values, in its unit; each compute target's validated and unvalidated counts, version
       labels and timestamp range, and its records by physical labels.
     - It also shows every named problem, never truncated.
  3. **`main.py --inventory`** reads the closed store with `read_inventory(args.database,
     factories)` **before `ray.init` (`main.py:97`)**, prints the report and exits.
     - `--show-all`, parsed today but read by nothing, maps to `verbose`. This closes
       `[show-all-flag-unused]`.
     - `--inventory` with `--drop` is refused.
  4. The 17 `inventory()` hooks and `config/sharding.py`'s `inventory_config` are deleted.
- **Acceptance.**
  1. **Tests on temporary stores built through the harness:**
     - `inventory_classes` accepts the registry (no `ValueError`), and each spec's leaves and
       parents resolve;
     - a store holding a trajectory, one of each compute target (failed and successful), and both
       potential types renders every field of P18's list;
     - problems are printed in full.
  2. `main.py --inventory` on a missing store fails cleanly, and needs no Ray.
  3. The suites give 09's counts plus the new tests.
  4. **Deliberate breakages caught:**
     - one spec's parent removed;
     - one leaf misnamed;
     - the type column dropped from a polymorphic parent's leaves;
     - `--inventory` moved after `ray.init` (an `ast` test).
  5. **Coverage, for the fingerprint** (U8, ruled 2026-10-12). A test walks the registry
     (`config/datastore.py`'s, once 05 has moved it) and puts every registered class in exactly one
     of three places: it declares a spec; it is a value or tag table read through an owner's spec,
     the test naming the owner and the slot; or it is excluded, by name, in a table in the test
     with a one-line reason. The test fails on a class in none of the three, and on an exclusion
     naming a class no longer registered. Deliberate breakages: the spec removed from one owner,
     and a new registered class with none, each fail it. Measured read-only at `7bb3efd`, the 30
     entries (`Datastore/SQL/Datastore.py:96-127`) leave three cases for this prompt to settle and
     record:
     - **`redshift`** and **`IntegrationSolver`** are registered owners that item 1's list does not
       name, and no spec references either, so the dependency rule does not bring them in. No
       driver writes them (§4.1; `redshift` is P12's issue). Each either gets a spec, which is
       cheap, or is excluded with that reason. A spec is preferred: an exclusion means a row that
       did appear would change no fingerprint.
     - **`GradientCoupledInstanton` has two child tables** and a spec one `values` slot (item 1).
       `GradientCoupledInstantonProfile` is written for every row and holds the radial profile,
       the science output; `GradientCoupledInstantonValue` is written only when
       `store_full_values` is set. Whichever does not take the slot is excluded, with that reason,
       and opened as an issue: a fingerprint of a GCI store then cannot see it. Whether to ask
       DatastoreKit for more than one value table per spec is the user's (§6.3).

**11 — Rehearse through both packages, RH2** (Opus).
- **What it does.** Runs §4.1's protocol with slug prefix `dk-and-rpk-migration-11`, at 10's tree.
- **Acceptance.**
  1. L1–L3 hold, and `main.py --inventory` reports no named problem on any store.
  2. Both provenance entries name their tag's commit, `editable: false`.
  3. **Against RH1, by §4.2 and §4.3:** each RH2 store equals RH1's store of the same mode, and so
     RH0's.
  4. **L4 against RH1:** the stage counts, the progress lines, and what the resume recomputed and
     pruned are RH1's. The prune at open is now the package's code.
  5. **Store hygiene by the package:**
     - `python -m datastorekit.tools.shard_key_audit` reports nothing on each store;
     - a `sharded_store copy` of `reference` opens read-only and compares equal to it by §4.2;
     - the copy is then deleted with `delete_store`.
  6. The board records **DatastoreKit's G4 as holding**.

**12 — Close the migration** (Sonnet).
- **What it changes.**
  1. **`CLAUDE.md`:**
     - the build-and-test section, with the counts measured at the close (P16), which closes
       `[test-counts-stale-in-claude-md]`;
     - "Critical rules", whose rules 2, 3 and 5 stay SI's but now cite the package's contract;
     - the protected list, as 09 left it, checked;
     - a new rule: **a defect in either package is reported upstream and never patched here.**
  2. **`.claude/rules/`:**
     - `test-selection.md` (counts);
     - `ray-dispatch.md`, `pool-read-apis.md`, `validate-on-startup.md`, `datastore-factories.md`:
       each checked against the packages, with the contract cited rather than copied.
  3. **The documents.** `.documents/architecture-summary.md`, `INFRASTRUCTURE.md` and `FILE_MAP.md`
     describe the packages: what SI supplies, what each package does. Dated records are left as
     they are.
  4. **The final measurements** at `HEAD` by both packages' scripts, saved, with the suites'
     counts.
  5. **In the verification document**, the G4 records for DatastoreKit's and RayPoolKit's
     extraction boards, drafted (P14). Neither is committed there.
  6. **The handover (§7)** to P2: the tag, how the audit reads the June and July stores from it,
     and the issues left open.
  7. **`.prompts/INDEX.md` and `.documents/OPEN-ISSUES.md`;** the board closed.
- **Acceptance.**
  1. The index's count and date agree with its rows.
  2. Nothing outside `.prompts/` and dated `.documents/` records names a deleted file as a current
     path.
  3. The default and integration runs pass.

## 3. Stores

**The campaign builds ten throwaway stores and touches no other.** Each rehearsal builds three,
for NN = 02, 07 and 11:
- `NN-reference.sqlite` and `NN-resumed.sqlite`, the dense mode;
- `NN-scalars.sqlite`, the scalars-only mode (§4.1).

RH0 also builds `02-scalars-2.sqlite`, to measure the scalars-only mode's reproducibility (§4.3;
added when prompt 02 was written).

They live with their shards under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`
(P2):
- They are outside the repository, so nothing can commit them.
- They keep SI's `.sqlite` suffix. The package names shards `<stem>-shard<NNNN><suffix>`, as SI
  does.
- `~/ScienceData` does not exist on 2026-10-11. 02 creates it, unless CPBH's campaign has by then.

11's `sharded_store copy` is the one store deleted by a prompt.

**No prompt deletes a rehearsal store.** RH0's and RH1's are compared with later ones. The user
removes them after 12's review, or not.

**The 02 and 07 stores are refused by the package**, as every SI store is (U31). That is expected,
and it is why §4.2 reads files directly. Neither 09 nor 10 opens one through the package.

## 4. The interfaces between prompts

- **01 ships:**
  - `installed_package_provenance()`, read by 03, 07, 08 and 11;
  - `tools/compare_stores.py` and its schema snapshot, run by 02, 05, 06, 07, 09 and 11;
  - the rehearsal scripts, which 07 and 11 run **unchanged**. A change to one is a deviation,
    logged and reviewed, since L4 compares their outputs.
- **01a ships** `ray_cluster.sh` (U9), with which 02, 07 and 11 start and stop SI's cluster under
  the shared rehearsal lock (§4.1).
- **02, 07 and 11 each add a section** to `.documents/dk-and-rpk-migration/verification.md`, which
  02 creates: §1 RH0, §2 RH1, §3 RH2. 12 adds §4, the close.
- **03 and 08 ship the pins**, exactly as §2.2 gives them, in `requirements.txt` and in no other
  file.
- **05 ships** `config/datastore.py`, with `factories`, `drop_groups` and `serial_batch_sizes`, and
  `config.sharding.vectorized_shard_key`. 09 passes the first and third to the package, and turns
  the second into tables.
- **06 ships** the `InflatonTrajectory` factories in their package form. 09 changes only their
  base's import.
- **DatastoreKit shipped `v0.3.0`** (§0.4), outside this campaign, from the brief (U3), and then
  `v0.4.0` (§0.5), which carries it unchanged. 08 pins `v0.4.0` (U10) and reads both SI checklist
  addenda.
- **07 ships** the tag `pre-datastorekit` (U7), which 12's handover cites.
- **09 ships** the rebuilt `live_pool`; 10's tests build their stores through it.

### 4.1 The rehearsal protocol

Run by the agent in the session (U2), for prompts 02, 07 and 11 only. NN is the prompt's number.

**The cluster** (*amended 2026-10-12 for U9*; [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md)).
- Before anything, the agent starts SI's cluster with 01a's
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration NN (RHk)"`.
  It takes the rehearsal lock shared with ChamPBH and SGK, and starts a cluster on `/tmp/ray-si`
  and SI's own ports, four CPUs, at `127.0.0.1:6390`. **If the lock is held, the script refuses
  and prints its owner; the agent stops and asks** (another project's rehearsal is running, or a
  stale lock needs the user). It never waits on the lock and never breaks it.
- It passes `127.0.0.1:6390` to every driver with `--ray-address`, and addresses every `ray` CLI
  call explicitly, as `start` prints. Four CPUs make the ten `FullInstanton` solves run in waves,
  so that an interrupt can fall inside the stage (build 2 below). The CPU count changes no result:
  each solve is one task.
- At the end, and after any stop, it runs `ray_cluster.sh stop`, which stops SI's processes alone
  and releases the lock. **No prompt runs `ray stop`** (§5 rule 17): it stops every Ray process on
  the machine, other projects' included.
- Other projects' clusters may be up meanwhile (isolated, not rehearsing); the agent leaves them
  alone. The machine should still be otherwise idle: the lock keeps rehearsals apart, not test
  suites, so the agent asks the user to hold other heavy work off if the load is high.

**The grid** (P1) is `quadratic-minimal.yaml`, a configuration in the tree:
- quadratic potential, `m = 10⁻⁵ M_P`, `φ₀ = 15 M_P`, `π₀ = 0`, 10 shards, tolerances `10⁻⁸`,
  100 samples per e-fold;
- the default instanton grid: `N_init = 20`, `N_final = 5`, and 10 values of `δN★` on
  `[0.1, 3.0]`;
- the homogeneous branch only (U11). The two gradient flags are still passed, since the driver
  mints their replicated rows whatever the targets (`config/pipeline_setup.py:95`):

```bash
PYTHONPATH=. ./venv/bin/python -u main.py --config quadratic-minimal.yaml \
    --database ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/NN-<store>.sqlite \
    --job-name dk-and-rpk-migration-NN-<build> --targets <targets> \
    --n-collocation-points 5 --alpha-regularization 0.01 --ray-address <address> \
    [--no-store-values] [--profile-db <path>]
```

where `<targets>` is `homogeneous` for every build, dense and scalars-only alike; the two modes
differ by `--no-store-values` alone (build 4 below). *It was `homogeneous gradient` for the
dense builds until U11.*

That is one trajectory, and ten each of `FullInstanton`, `SlowRollInstanton` and
`CompactionFunction`. It writes every table SI registers but seven:
- `GradientCoupledInstanton`, `GradientCoupledInstantonValue` and
  `GradientCoupledInstantonProfile`, since no rehearsal builds the gradient branch (U11). Their
  factories are covered by the integration suite;
- `redshift` and `IntegrationSolver`, which no driver writes;
- `QuarticPotential` and `quartic_coupling`, since the grid is quadratic. Their factories are
  covered by the integration suite and by 10's tests, which build both potential types.

No wall-clock budget is set, so no solve depends on load. The homogeneous branch was stored in
about 35 s at 02's first attempt. 02 records each build's wall time. If `reference` takes more
than 45 minutes, 02 stops, and the user rules on a smaller grid.

**The builds.** Each runs detached. Its output goes to
`~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/`, with the driver's exit
status appended.
1. **`reference`**, on the `reference` store, straight through, with `--profile-db`. This exercises
   `ProfileAgent` through whichever layer is in use.
2. **`resumed-a`**, on the `resumed` store. `interrupt_when.py` sends `SIGTERM` once the log shows
   `STAGE 2: FULL MSR INSTANTONS` and the stated delay has passed. The delay is set from
   `reference`'s stored timestamps, to fall while some `FullInstanton` rows are stored and others
   are not; the window is wider, from the first `FullInstanton` stored to the last
   `CompactionFunction` stored, so that the store is left partial. If the signal lands outside
   it, the prompt may retune the delay and rerun `resumed-a` on a fresh store, twice at most, and
   records what it got. *It was `STAGE G` until U11.*
3. **`resumed-b`**, on the same store, straight through. SI always prunes unvalidated rows at open
   (`--prune-unvalidated` is `store_true` with `default=True`).
4. **`scalars`**, on the `scalars` store, with `--no-store-values` and **`--targets homogeneous`
   only**, straight through. This exercises the unified pipeline and the scalars-only storage
   path. (The gradient branch was left out of this build because of
   `[gci-main-no-store-values-crash]` (§0.2) before U11 left it out of every build.)
5. **`scalars-2`**, at RH0 only: build 4 again, into `02-scalars-2.sqlite` (§4.3).

The agent waits on each build's exit (a background task), not by polling.

**What must hold.**
- **L1 — every build ends as it should.**
  - `reference`, `resumed-b` and `scalars` exit 0, with every stage's "ALL WORK ITEMS COMPLETE".
  - `resumed-a` exits by the signal.
  - No traceback in any log.
- **L2 — the resume is the reference.**
  - `compare_stores reference resumed` is §4.3's result.
  - The resume recomputed nothing it had stored, by `stage_counts.py`.
  - The prune at open removed only unvalidated rows, by its printed report.
- **L3 — every reader**, run on the closed `resumed` and `scalars` stores, writing under
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/NN-readers/`:
  - `main.py --inventory` on both. At 02 and 07 it goes through SI's pool; at 11 through
    `read_inventory`.
  - `plot_InstantonSolutions.py` on both. On `scalars`, with `--no-store-values`, its
    `scalar_data.csv` is compared byte for byte, at 07 and 11, with 02's.
  - *`plot_GradientCoupledSolutions.py` is not run (U11): no rehearsal store holds the gradient
    branch.*
  - Each exits 0. The plot scripts open read-write pools under `"2026.3.0"` (P9, P10), so the
    check that the readers changed nothing is `compare_stores` of each store before and after
    them. It must be empty but for **one `version` row, labelled `2026.3.0`**, and bookkeeping.
- **L4 — equal to the previous rehearsal.** Against the campaign's previous rehearsal (none for
  RH0): each stage's work-item counts, and the rows the resume pruned and recomputed. If L1–L3
  pass and L4 differs, that is a finding to explain, not an automatic failure.

**If a comparison misses** (§4.3), the prompt stops, records `compare_stores`'s full output, and
changes no code. Where the cause lies:
- **RH0's miss** is SI's (02).
- **RH1's** is in 03–06.
- **RH2's** is reported to the package's repository as a defect if it is the package's (§5 rule
  11), and is SI's if it is in 09–10.

### 4.2 Comparing stores by value

`tools/compare_stores.py A B` compares two SI stores by what they hold, never by how they are laid
out. It **reads both through `sqlite3` with `mode=ro` only, and never through either layer**, so
it reads a store of either format: SI's (absolute shard records) and the package's (bare names,
`replication_in_flight`). It finds a store's shards by the glob `<stem>-shard*<suffix>` beside the
primary, and checks their count against the primary's `shards` table.

- **What it compares:** every row of every client table, on every shard.
  - A table's rows are taken as a multiset of **identities**. A row's identity is its columns, less
    the bookkeeping ones, with each reference replaced by the identity of the row it names,
    recursively.
  - A reference is a foreign-key column (`PRAGMA foreign_key_list`) or one of **the four
    polymorphic references**: `potential_serial` by `potential_type` on `InflatonTrajectory`, and
    `diffusion_serial` by `diffusion_type` on `FullInstanton`, `SlowRollInstanton` and
    `GradientCoupledInstanton` (*four, not two: corrected at 01's review*). The tool carries their
    type maps as data, tested against SI's registries (01).
  - A float is compared by its stored bits (`float.hex`).
  - **A JSON column** (`fields_json`, `diagnostics_json`, `metadata`) is parsed and compared
    structurally, its floats by their bits. Its **timing keys** (`compute_time` and the Picard
    timings; 01 derives the list by reading every compute target, and tests it) are bookkeeping.
  - So serials, shard assignment, insertion order and timings do not matter, and every stored
    science value does.
- **Bookkeeping**: `serial` and `timestamp` everywhere, `job_name`-like columns if any, and the
  JSON timing keys. They are reported, never compared.
- **Not compared:**
  - the primary's own tables (`shards`, `shard_key_config`, `shard_keys`, `replicated_tables`,
    `sharded_tables`, and `replication_in_flight` where present);
  - a replicated table's copies on other shards. Each shard's copy is checked equal to the
    others', and a difference is reported.
- **Its output:**
  - per table, the rows in A only and in B only, each with its identity resolved to physical
    labels;
  - for a row of the same lookup key in both whose science columns differ, each differing column
    with both values and their relative difference.

  It exits 0 when nothing differs, 1 when something does, and 2 when it cannot read a store.
- **The schema snapshot:** each client table's columns (name, type, nullability, primary key) and
  indices, as sets, written as JSON for one store and compared for two. A difference is a finding,
  not a miss. The package orders its prepended columns `serial`, `version`, `timestamp`,
  `stepping` (contract §2).

It stays in the tree after the campaign, for P2's comparison of its rebuilt grids with the June
ones, where the expected answer is a difference.

### 4.3 Reproducibility, and the criterion it sets

Nothing in a build should depend on the layer:
- each trajectory and each instanton is integrated in one Ray task;
- no solve is budgeted by the clock (and no rehearsal builds the gradient branch, U11);
- what is stored is what the integrators return.

So the expectation is that two builds of one grid agree **bit for bit**, once timings are set
aside. RH0 measures this rather than assuming it: `reference` and `resumed` compute every point
independently, on one tree, and so do `scalars` and `scalars-2`.
- **If RH0's two dense stores are equal, and its two scalars-only stores are,** RH1 and RH2 are
  held to equality with RH0's stores of the same mode.
- **If they differ,** the cause is recorded, and the user rules on RH1's and RH2's criterion before
  05–07 are written. No tolerance is chosen by an agent.

### 4.4 Rollback

Each prompt is one commit, reverted by `git revert`.
- **The venv is shared**, so reverting 03 or 08 also needs `./venv/bin/pip uninstall -y <package>`.
- **Reverting 04 or 09 alone needs nothing in the venv.** An installed, unimported package is
  inert.
- **Reverting 09 makes RH2's stores unreadable by the tree**, as every package-written store is to
  SI's layer. They are throwaway (§3).
- **The campaign runs in the main checkout**, on its branch (P15), not a worktree: a worktree has
  no venv of its own.

## 5. The rules this campaign runs under

The project-wide ones in `CLAUDE.md` (its critical rules, the protected list, the units
convention), plus:

1. **One commit per prompt.** The commit boundary is the rollback boundary.
2. **Every prompt writes a results note** to `.documents/dk-and-rpk-migration/NN-<name>.md`, using
   §5.1. It classifies every deviation as `STRUCTURALLY REQUIRED`, `IMPLEMENTATION CHOICE` or
   `UNINTENDED DRIFT`.
3. **Every prompt updates `IMPLEMENTATION_STATE.md` in its own commit.** Whenever a §3 or §4 entry
   moves, `.documents/OPEN-ISSUES.md` is updated in the same commit (`CLAUDE.md`).
4. **Do not fix things the prompt did not ask for.** Record them, and open a §3 issue.
5. **Commit messages** in the repository's form: an imperative title, a body, and a
   `Co-Authored-By:` line naming the model.
6. **Verification documents are additive.**
7. **Existing tests are not modified**, except where a prompt names the test and the reason: 05's
   four stubs, and 09's `live_pool` and `test_grid_builder_integration.py`.
8. **Deliberate breakage.** Each prompt names mutations its tests must catch. The results note
   records each as a diff, exactly as applied, so that the orchestrator can replay it with
   `git apply`. Mutations are never committed.
9. **No stored science value changes.** §4.2 is the measurement, and a prompt that cannot keep it
   stops.
10. **Tests.**
    - No new test opens a store outside a `tempfile` directory.
    - A new test that needs Ray is `integration`-marked and says why it cannot do without Ray.
    - A rehearsal's reads of its own stores are verification steps, not tests.
11. **A defect in a package is not patched or worked around in SI.** The prompt stops and records
    it. The user reports it to that package's repository, where it is fixed in a new release, and
    a new pin prompt moves SI to it.
12. **No change is made in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit by a prompt here.**
    Their repositories are read, and the two packages' measuring scripts are run from their roots
    with their own venvs. The DatastoreKit release U3 asks for is that repository's own work, from
    the brief.
13. **Pins.** Each pin is a tag, in a commit of its own, never an editable install. SI keeps its
    own `ray` and `SQLAlchemy` pins.
14. **Rehearsals** follow §4.1, and only 02, 07 and 11 run `main.py` on a store.
15. **Protected files and formatting.** A prompt touches a file on `CLAUDE.md`'s protected list only
    if it names it and says what changes (`CLAUDE.md:91-92`). It never reformats or reorders what
    it does not change (`CLAUDE.md:111-112`). A new file may be formatted with `ruff format`.
16. **Which tests a prompt runs** (P16):
    - the default run and the `integration` run, always, since every code prompt touches
      `Datastore/`, `config/` or the drivers;
    - and the `slow` block once more in 09, which touches `ComputeTargets/`
      (`.claude/rules/test-selection.md`).
17. **Ray** (U9, ruled 2026-10-12). **No prompt runs `ray stop`**, which stops every Ray process on
    the machine. A cluster is started and stopped only by 01a's `ray_cluster.sh` (from 01a on),
    and every driver and `ray` CLI call is given its address. The `integration` suite runs as
    `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration …`, so that `live_pool`'s bare
    `ray.init()` starts a private instance and can never attach to another cluster.
18. **The rehearsal lock** (U9). A rehearsal (02, 07, 11) holds
    `~/ScienceData/.rehearsal-lock` from before its cluster starts until after it has stopped
    ([`rehearsal-lock-brief.md`](rehearsal-lock-brief.md) §2). A held lock is a stop, never a
    wait.

### 5.1 The results-note template

- the subject, commit and result;
- **What shipped**;
- **Deviations from the prompt**, each classified;
- **Verification performed**, with every count against §0.2's;
- **The deliberate-breakage record**;
- **Observations not acted on**;
- **State handed to the next prompt**.

## 6. Decisions

### 6.1 Ruled by the user

Each row gives the planner's recommendation first. **All eleven are ruled.** U3, U8 and U9 were
ruled on 2026-10-12, U10 on 2026-10-19 and U11 on 2026-10-20, as their rows say. **U1, U2 and U4–U7 were ruled on 2026-10-12 as recommended**:
the recommendation in each row is the decision, and the alternative beside it is rejected.

| | Recommended | The alternative, and why not |
|---|---|---|
| **U1** — the order | **RayPoolKit first**, as in CPBH. Its swap deletes `RayTools/`, rewrites 3 imports, drops a private name and changes no call site. It also removes `RayTools/RayWorkPool.py:23`'s layer import, so the DatastoreKit swap never touches `RayTools/` | DatastoreKit first, as in SGK. SGK's reason (a test edited only to be deleted) has no counterpart here, and RayPoolKit's U12 exception would be needed |
| **U2** — the rehearsals | **The agent runs them** (§4.1): a reference, a killed-and-resumed build, a scalars-only build and the readers, at RH0, RH1 and RH2, on the grid of P1 | The user runs every build. Straight-through builds only, which would leave the prune at open unexercised under real Ray |
| **U3** — `DatastoreObject.timestamp` (**ruled 2026-10-12**) | **Fix the package, not the client.** DatastoreKit's `DatastoreObject` gains an optional `timestamp` argument and a read-only property, in a release requested by [`datastorekit-v0.2.4-brief.md`](datastorekit-v0.2.4-brief.md) and **delivered as `v0.3.0`** (§0.4), carried unchanged into `v0.4.0` (§0.5), which 08 pins (U10). The package already owns the column (it prepends it, stamps it and reports it), and every client writes it; only the object's slot was missing. SI's 24 sites then change only an import (09), and the provenance footers keep their timestamps. *The planner first recommended a class of SI's own; the user asked whether it belonged in DatastoreKit, and ruled that it does* | A `TimestampedDatastoreObject` of SI's own, the 14 classes moved onto it before the swap: a layer-shaped class kept in the client after the layer has gone. It was the fallback had the release been late; it was not. Dropping the timestamp: the footers lose the row's creation time, which `metadata-annotations` added on purpose |
| **U4** — `InflatonTrajectory` under the replicated protocol | **Do all four, before the swap** (06): the cascade that fixes the orphan bug; `owner_column` on the value table, without which the package refuses that cascade; `validated_column` with `revalidate`, so that an interrupted validate is repaired at open rather than refused; and the `prune` keyword | The keyword only, the checklist's minimum. It leaves the orphan bug, and a store that an unlucky Ctrl-C makes unopenable |
| **U5** — a drop that leaves references | **Refuse before Ray starts, naming the groups to add** (09), as CPBH's U4 | Expand the request silently, with a notice; or leave the refusal to `ShardedPool` at open, which is later and names tables, not groups |
| **U6** — the inventory | **Port it** (10): `inventory_spec` on the factories, `read_inventory` on a closed store, an SI report. It also brings the problem checks (orphans, unresolved parents) that the old inventory never had | Keep a reader of SI's own over the closed store: a second implementation of what the package now provides |
| **U7** — when, relative to P2 | **Before P2.** 07 tags its commit `pre-datastorekit`, the last commit on SI's own layer, rehearsed. P2's audit of the June and July stores runs from a worktree at that tag | After P2's audit, at the start of P2 proper, as the checklist advises. That interleaves two campaigns, and P2's first builds would be on the old layer |
| **U8** — spec coverage, for the fingerprint (**ruled 2026-10-12**) | **10 proves that every registered class is covered** (10's acceptance item 5): a spec of its own, read through an owner's, or excluded by name with a reason, enforced by a test. SGK is extracting its `RunRegistry` into RunRegistryKit, which SI is expected to adopt after this campaign; its store fingerprint is taken through `read_inventory`, which reads only the classes that declare a spec and passes over the rest **silently**, and the user ruled that its store layer will not run without a fingerprinter. Item 1's "each factory whose class the report covers" is the right test for a report, not for a fingerprint. Measured at `7bb3efd`, item 1's list misses `redshift` and `IntegrationSolver`, and `GradientCoupledInstanton`'s second child table cannot be reached by a spec. The reasoning is SGK's `docs/runregistry-extraction-audit.md` §0 (D4, D5) and §7. Adopting RunRegistryKit stays out of this campaign's scope | Leaving item 1 as written: a store fingerprint would omit two registered classes and one table of results without saying so |
| **U9** — other projects' Ray clusters (**ruled 2026-10-12**) | **Isolate, and take a shared lock.** SI's cluster runs on its own temp dir and ports and is stopped by a targeted stop, never `ray stop`; one lock, `~/ScienceData/.rehearsal-lock`, shared with ChamPBH and SGK, lets one rehearsal run at a time. ChamPBH adopts the same targeted stop, and SGK takes the lock (its in-process clusters are already isolated). The contract is [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md); 01a implements SI's side. Raised at 01's review: SGK's rehearsal ran beside this campaign's suites, ChamPBH's protocol runs a bare `ray stop`, and ChamPBH's BBN wall-clock limit makes its results sensitive to load | Moving SI's campaign to another machine: a rebuilt venv, two unpushed branches, and sibling repositories at the same paths, for nothing isolation does not give. Interleaving by hand, with no lock: a `ray stop` from either side still kills the other's build |
| **U10** — which DatastoreKit release (**ruled 2026-10-19**) | **Pin `v0.4.0`** (§0.5). It is `v0.3.0` plus one module, `store_fingerprint.py`, which the layer never calls and SI does not import; `object.py` and `store_inventory.py` are unchanged, so nothing in 08–11 changes but 08's pin and the commit it checks. SI's checklist addendum offers `v0.3.0` or `v0.4.0`, and G4 reads "`v0.3.0` or later". RunRegistryKit's `[stores]` extra requires `datastorekit>=0.4.0`, so the RunRegistryKit adoption that follows this campaign (U8, §7) starts from SI's pin. *The user asked to adopt `v0.4.0` once it was released* | Stay on `v0.3.0`: the same layer, and a second pin commit owed to the RunRegistryKit campaign |
| **U11** — the gradient branch in the rehearsals (**ruled 2026-10-20**) | **Drop it from every build.** 02's first `reference` ran 5 h 36 min and was stopped: none of the first four gradient solves finished, each over five hours at full CPU with every inner Picard step failing and λ halved again and again (`[gci-picard-inner-fails-on-rehearsal-grid]`). Solves that do not converge will not start to; the campaign is about the storage layer, not the solver. The dense builds become `--targets homogeneous`, the interrupt moves to `STAGE 2`, and `plot_GradientCoupledSolutions.py` leaves the readers. The gradient tables are covered by the suites only. *Ruled by the user, who chose it as the only viable option* | A wall-clock budget: bounded, but where a solve stops would depend on load, so two builds could differ and §4.3's bitwise criterion would mean nothing. A converging configuration, or a cap by iteration count: physics work outside this campaign (P3's) |

### 6.2 Proposed by the planner

Accepted as proposed unless a ruling is given beside the proposal. The user ruled U1, U2 and
U4–U7 on 2026-10-12 and gave no ruling on any of P1–P19, so all nineteen stand as proposed.

- **P1 — the rehearsal grid** is `quadratic-minimal.yaml`, with both branches, the gradient branch
  at `n = 5`, `α = 0.01`, and a scalars-only build of the homogeneous branch (§4.1). It is the
  cheapest configuration in the tree that writes every table a quadratic run can write. Its mass,
  `10⁻⁵ M_P`, is the one at which Phase A's gradient solves stopped at an iteration cap in about
  5 minutes, not at a wall-clock budget. If 02's `reference` exceeds 45 minutes, 02 stops for a
  ruling. *Overtaken 2026-10-20 by U11: the gradient branch is dropped from every build, since
  its solves did not finish in over five hours at 02's tree.*
- **P2 — the rehearsal stores** live under
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`, with the `.sqlite`
  suffix (§3), beside CPBH's `~/ScienceData/ChamPBH-rehearsals/`.
- **P3 — comparison by value** (§4.2), by a lasting tool in `tools/`, tested and
  layer-independent. It is SI's own, modelled on CPBH's, because SI's references and JSON columns
  need handling CPBH's does not. Whether the three clients' tools should one day be one tool in
  DatastoreKit is noted, not proposed.
- **P4 — the criterion** is RH0's measured reproducibility (§4.3): bitwise if RH0 is bitwise, and
  otherwise the user's ruling.
- **P5 — run provenance in the drivers' output**: one line, never a refusal (01). It is in
  `utilities.py`, named as a protected file, in the shape of SGK's `package_provenance()`.
- **P6 — `Datastore/__init__.py` and `Datastore/SQL/__init__.py` become empty files.** The
  factories stay where they are. Whether the `Datastore` package is renamed is left for another
  day.
- **P7 — the 12 lookup-only pool sites keep `store_handler=None, persist_handler=None`** (RayPoolKit
  checklist item 4, advice), so 04's diff is the imports and `_default_store_handler`.
- **P8 — a helper for the shard-key mapping**, `config.sharding.vectorized_shard_key(key)`. It
  gives one definition of the field name, `"delta_Nstar"`, for the 15 call sites. An `ast` test
  pins its use.
- **P9 — no `VERSION_LABEL` bump**, and the plot scripts' `"2026.3.0"` is left as it is. Nothing
  the code computes changes, and no store crosses the swap. The stale plot label is opened as
  `[plot-scripts-stale-version-label]`, for P2 to settle when it bumps the label.
- **P10 — the plot scripts keep read-write pools.** A read-only pool would refuse a miss
  (`ReadOnlyMiss`) where today a lookup inserts a row. Finding where that happens is a change of
  behaviour this campaign does not need. Read-only plot pools are recorded as a goal, under the
  same issue.
- **P11 — `--inventory` refuses between 09 and 10**, with a message, rather than failing with an
  `AttributeError`.
- **P12 — `redshift` stays registered**, and the batch sizes move verbatim, `temperature`
  included. Removing either changes the schema or the data the swap moves. Opened as
  `[redshift-registered-in-neither-table-list]`.
- **P13 — stale prose.** A statement that a prompt's own commit makes false is corrected in that
  commit (04, 06, 09). The rest of the rewrite of the documents, `CLAUDE.md` and the rules is
  12's. Dated records and `.prompts/` are left as the record of the tree they describe.
- **P14 — the gates.** This board records each G4 when it holds (04, 11). Recording G4 on
  DatastoreKit's and RayPoolKit's extraction boards is a records commit in each of those
  repositories: 12 drafts the text, and the user makes the commits, or has a session there make
  them.
- **P15 — the branch.** `dk-and-rpk-migration`, cut from `main` with the planning commit on it,
  and merged into `main` at the close.
- **P16 — the tests each prompt runs** (§5 rule 16). It follows `.claude/rules/test-selection.md`;
  the counts are re-measured, and corrected in `CLAUDE.md` at the close.
- **P17 — `prune` in all 12 hooks**, not only `InflatonTrajectory`'s. Each change is one
  parameter name. It gives one convention, the contract's, where the checklist's minimum would
  leave two.
- **P18 — the inventory report shows at least what today's does** (10, item 2), and every named
  problem in full. Its layout is new, and nothing parses it.
- **P19 — results notes and the verification document** go in `.documents/dk-and-rpk-migration/`,
  SI's convention for a campaign's results (`CLAUDE.md`, "Campaigns"), rather than CPBH's
  `logs/`.

### 6.3 Left for the user

- ~~Before 01: the rulings above~~ (ruled 2026-10-12).
- **At 10:** whether to ask DatastoreKit for more than one value table per spec, so that a
  fingerprint can see both of `GradientCoupledInstanton`'s child tables (U8). DatastoreKit's
  `fingerprint` plan left this out of `v0.4.0` explicitly, "until SI's prompt 10 settles it and
  the user asks" (its README §1, out of scope), so a request would be a new DatastoreKit release
  and a new pin prompt here (§5 rule 11).
- **At 07:** pushing the tag.
- **At the close:**
  - removing the rehearsal stores (§3);
  - the two G4 records (P14);
  - the plot scripts' label and pools (P9, P10);
  - whether to rename the `Datastore` package (P6).

## 7. What this campaign hands to P2

- **The June and July stores become unreadable by the tree at 09** (U31). They stay on disk, and
  stay readable:
  - from the tag `pre-datastorekit`, in a worktree that uses the main checkout's venv;
  - by `tools/compare_stores.py`, at any commit after 01.
- **P2's first prompt, `[hfp-closed-form-audit-not-run]`, reads them at the tag.** Its own
  builds, and the re-run of the June grids, go through the packages into fresh stores.
- **`tools/compare_stores.py`** is the tool for P2's comparison of its rebuilt grids with the
  June ones. There a difference is the expected result, and the tool names it value by value.
- **`[inflaton-trajectory-prune-orphans-value-rows]` is closed** by 06. Any June store that was
  pruned after an interrupted run may hold orphans. P2 reads those stores and does not resume
  them, so this matters only if a June store is reopened read-write at the tag.
- **RunRegistryKit comes next, in a campaign of its own** (U8, U10; *added 2026-10-19*). Its SI
  checklist (RunRegistryKit `docs/adoption/stochasticinstantons.md`, with
  `docs/adoption/v0.2.0/stochasticinstantons.md`) says SI adopts `v0.2.0` directly, the core at
  any time and the store layer only after this campaign. This campaign leaves what the store layer
  needs: `datastorekit` `v0.4.0` pinned (08), `config/datastore.py`'s registry (05), and specs that
  cover it (10). The checklist also offers replacing `utilities.installed_package_provenance` (01)
  by `runregistrykit.package_provenance`, and advises building its format-bump guard with the
  fingerprinter, right after 10. Both are that campaign's, not this one's.
