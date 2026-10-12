# Brief: a release whose `DatastoreObject` carries the row's timestamp

*Outcome (2026-10-12): released by DatastoreKit's `object-timestamp` campaign as **`v0.3.0`** (tag
object `bf0a3b2`, commit `2f5417e`), with `timestamp` keyword-only. The brief below is unchanged,
as the record of the request; the campaign README's §0.4 records what was delivered.*

**For:** the agent that plans a campaign in DatastoreKit (`/Users/ds283/Documents/Code/DatastoreKit`)
to release the next `datastorekit`, called **`v0.2.4`** here, under DatastoreKit's `CLAUDE.md` and
its campaign conventions. The version number is DatastoreKit's to choose (§4).
**Written:** 2026-10-12, from a Claude Code session in StochasticInstantons (SI), with the user,
while planning SI's adoption campaign (`.prompts/dk-and-rpk-migration/` in SI, README §6.1, U3).
**Trees:** DatastoreKit at `83068cb` (`v0.2.3` is `0de2b16`); SI at `7bb3efd`; SGK and ChamPBH
read through `git` at their `HEAD`s of 2026-10-12.

**This brief is evidence to check, not a specification** (DatastoreKit `CLAUDE.md` invariant 7).
The user's ruling, in §1, is a ruling. Everything else is a finding with its citation, or a
recommendation marked **Advice:**. Where this brief and DatastoreKit's own records disagree, the
records are right, and the disagreement is worth reporting back. The campaign's name, its decision
numbers and its shape are DatastoreKit's to choose.

## 1. What is asked, and who ruled it

**The user's ruling (2026-10-12):** make this change in DatastoreKit, not in SI. SI keeps its
objects' `timestamp`, and pins a release in which `DatastoreObject` carries it.

**The change asked for.** `datastorekit.DatastoreObject` (`datastorekit/object.py:4-21` at `v0.2.3`)
gains:
- an optional constructor argument, `timestamp: Optional[datetime] = None`;
- a read-only property `timestamp` returning it.

Nothing the layer writes changes, and nothing it reads. **The layer does not set the value.** A
factory that reads a row of a class registered with `"timestamp": True` may pass the row's
`timestamp` to the object it builds, as SI's factories do today. An object not yet stored, or read
from a table without the column, has `timestamp` `None`.

## 2. Why it belongs in the package

**The package already owns the column, but its object cannot hold the value.**
- A factory whose `register()` returns `"timestamp": True` gets a `timestamp` `DateTime` column,
  which the schema builder prepends (`datastorekit/SQL/schema.py:141-144` at `v0.2.3`; contract §2,
  `timestamp`).
- The actor stamps it at insert (`SQL/Datastore.py:809-815`). A replicated write stamps every shard
  with the driver's one timestamp (`:810`, and `insert_timestamp=` at `SQL/ShardedPool.py:3288`,
  `:3316`, `:3343`, `:3480`, `:3493`). The check at open repairs a missing row only if its
  timestamp is the record's start (contract §2).
- The inventory reports the earliest and latest per class (`store_inventory.py:391`).
- So the column is the package's, from schema to replication to inventory. What a client cannot do
  with the package's `DatastoreObject` is hold the value once it has read it back. Each client
  that wants to must add the attribute on a subclass of its own.

**All three clients write the column; one reads it back.** By `git grep` of each client's factory
package at its `HEAD` on 2026-10-12:
- SGK: 19 factory files register `"timestamp": True`. ChamPBH: 16. SI: 21 of its 22.
- **SI reads it back.** Its `DatastoreObject` takes `timestamp` and exposes it
  (`Datastore/object.py:25-30`, `:43-45` at `7bb3efd`). It was added at SI `51b04f8` (2026-06-21,
  "Surface row-creation timestamps via DatastoreObject").
  - 14 classes call `DatastoreObject.__init__(…, timestamp=…)`, every one by keyword.
  - 10 subclasses pass `timestamp=` through `super().__init__`.
  - SI's factories pass `timestamp=row.timestamp` from `build`.
  - The plot adapters read `.timestamp` for the provenance footers of every figure
    (`plotting/adapters/full.py:61`, `gradient.py:133`, `slow_roll.py:66`; `plotting/provenance.py:41`).

  DatastoreKit's SI checklist lists all 24 sites (`docs/adoption/stochasticinstantons.md` item 2).
- **SGK and ChamPBH** read it back nowhere. Neither has an attribute or property named `timestamp`
  or `_timestamp` on any class outside its layer (`git grep` for `self.timestamp =`,
  `self._timestamp`, `def timestamp(`, excluding `prompts/` and `docs/`).

**What SI would do otherwise.** It would add a `TimestampedDatastoreObject(DatastoreObject)` of its
own, and move its 14 classes onto it before the swap. That is a layer-shaped class kept in the
client after the layer has gone, and each future client that wants the value writes it again.
With the release, SI's 24 sites work unchanged once their import is rewritten.

**No DatastoreKit decision chose to leave it out.** `datastorekit/object.py` is SGK's file,
carried over at extraction (`PROVENANCE.md:19`), and SGK's never had the attribute. The SI
checklist records the difference and leaves the choice to SI (item 2, "Whether SI drops the
timestamp or keeps it on its own classes is SI's choice"). That choice has now been made, as a
request to the package.

## 3. What to check before planning

These are the brief's findings, to be measured again at DatastoreKit's `HEAD`:
1. **Nothing in the package inspects an object's attributes in a way a new one would change.** At
   `v0.2.3`, `git grep` over `datastorekit/` (less `tests/`) finds no `__dict__`, `vars(`, `__eq__`
   or `__getstate__`. The layer reads `_my_id`, `store_id`, `_new_insert` and `_updated` (contract
   §6). Check that a replicated store's comparison of the controller's answer with each replica's
   (`owned_serials`, `_my_id`) does not reach the new attribute either.
2. **Every existing call keeps working.** The neutral client calls `super().__init__(store_id)`
   positionally (`datastorekit/tests/client/objects.py:29`, `:37`, `:51`, `:69`;
   `tests/client/instances.py:49`). SGK and ChamPBH pass `store_id` alone. A defaulted second
   argument changes none of them.
3. **No client class would collide with a read-only base property.** A subclass that assigns
   `self.timestamp = …` would raise `AttributeError` under a property without a setter. The brief
   found none in any client (§2). SI's test stand-ins that set `self.timestamp`
   (`tests/test_plot_adapters_golden.py:141`, `:186`; `tests/test_plot_diagnostics_figures.py:75`,
   `:91`) are plain classes, not subclasses of `DatastoreObject`.
4. **Pickling.** An object with one more plain attribute crosses Ray as before (contract §6,
   "Picklable, defined at module level"). A `datetime` pickles.

## 4. What a release would carry

**Advice**, for DatastoreKit to adopt or change:

- **The code.** `datastorekit/object.py` only. The form SI uses today, so that SI's calls are
  unchanged:

  ```python
  def __init__(self, store_id: Optional[int], timestamp: Optional[datetime] = None):
      self._my_id = store_id
      self._timestamp = timestamp

  @property
  def timestamp(self) -> Optional[datetime]:
      return self._timestamp
  ```

  - A keyword-only `timestamp` would also serve SI, whose calls are all by keyword. Positional or
    keyword is DatastoreKit's choice; this brief has no preference beyond SI's calls working.
  - The docstring should say who sets the value (a factory, from the row), and when it is `None`.
- **What it does not do.** The layer does not fill `timestamp` on an object it stores, or on one a
  get answers. The value is the factory's to pass. Filling it after a store (the inserter knows the
  timestamp it wrote) is a possible later change. It is not asked for here, and SI does not do it
  today (`Datastore/object.py:26-29`: "populated only when an existing row is re-fetched").
- **The tests**, in DatastoreKit's suite (no client is imported):
  1. the object takes `timestamp` and returns it; without it, `timestamp` is `None`;
  2. a neutral-client factory whose `build` passes the row's `timestamp` returns objects carrying
     the stamp the actor wrote, through the stand-in pool. A replicated class's object carries the
     one timestamp of its replicated write on every shard;
  3. the property has no setter (`AttributeError` on assignment);
  4. the neutral client's existing objects, which pass no timestamp, are unchanged: their tests
     pass as they stand;
  5. the object round-trips through `ray.cloudpickle` with its timestamp, as `test_factory_instances`
     test 5 does for a factory.
- **The documents.**
  - `docs/client-contract.md`: a §9 subsection for the change, adding a row to §6's table (what the
    layer reads from a stored object). The layer *reads* nothing new, so the row says what the
    object offers and who fills it. §1–§9.5 stay as written (`CLAUDE.md` invariant 6).
  - `docs/adoption/README.md`: a `v0.2.4` addendum.
  - `docs/adoption/stochasticinstantons.md`: a `v0.2.4` addendum superseding item 2's
    `DatastoreObject.timestamp` paragraph, and item 4's line on it. With the release, the 24 sites
    work as they stand, and the pin moves to `v0.2.4`.
  - `docs/adoption/champbh.md` and `docs/adoption/secondarygwkit.md`: an addendum each, saying that
    nothing changes for that client, which may stay on its pin.
  - `PROVENANCE.md`, `README.md` ("Status", "Changes"), the version in `pyproject.toml`, and the
    campaign's own verification record, as the `v0.2.2` and `v0.2.3` releases did.
- **The version.** The change adds to the public API and changes no behaviour. Whether that is
  `v0.2.4` or `v0.3.0` is DatastoreKit's call, and SI's plan is corrected to match.
- **The release.** CI green at both tested ends, then the tag pushed to the remote, as for
  `v0.2.3` (the `factory-defaults` campaign, prompt 02).

## 5. What each client does with it

- **SI** pins the release in its adoption campaign (its prompt 08, written after its prompt 07's
  review). Its prompts 01–07 do not wait for the release. If the release has not been tagged when
  08 is due, SI's fallback is the class of its own described in §2, recorded as the rejected
  alternative of its U3.
- **ChamPBH** is mid-way through its adoption, pinning `v0.2.3` (its prompt 07). Nothing in this
  release reaches it. **Advice:** say in its addendum that it may stay on `v0.2.3` or move in a
  commit of its own, as it chooses.
- **SGK** has `v0.2.2` pinned; the same holds.

## 6. Rules that come with this request

- **No change in a client.** The campaign reads SI, ChamPBH and SGK through `git` only, as the
  checklists were measured. It edits none of them.
- **Nothing the layer writes or reads changes**, and no message, refusal or exception.
- **Nothing else rides in the release.** A defect found while doing this is recorded and opened as
  an issue on DatastoreKit's board, not fixed in this release, unless the user rules otherwise.
- **The gates.** G4 reads "SI has adopted `v0.2.4`" once the release exists. G2 and G3 read as
  they do now.

## 7. First steps

1. Re-measure §3's four points at DatastoreKit's `HEAD`.
2. Read `datastorekit/object.py`, contract §2 (`timestamp`) and §6, and items 2 and 4 of the SI
   checklist.
3. Plan the campaign under DatastoreKit's conventions: decisions recorded, one commit per prompt,
   the tag made by a prompt that says so.
4. When the release is tagged, tell the user the tag object and commit. SI's prompt 08 is written
   from them.
