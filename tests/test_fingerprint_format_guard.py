# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Guard the fingerprint format against spec changes (rrk-adoption prompt 02, item F3; campaign
README §0.3 and §6.2, P5; RunRegistryKit's docs/adoption/README.md §6, "The Q5 guard", and its
addendum "The Q5 guard under DatastoreKit v0.5.0").

``config.fingerprint.FINGERPRINT_FORMAT`` is a number the author bumps when what the inventory
records changes. Nothing makes the bump happen, and the golden fingerprint says only that data
changed, not that the format was forgotten. This module pins, for each format that has a pin
(``config.fingerprint.SPEC_DIGESTS``), the SHA-256 of the canonical JSON of every
``inventory_spec()`` in the registry, in registry order, as ``[class, digest]`` pairs: 24 of them,
one per registered class with a spec (22 ``inventory_spec`` definitions serve 24 classes, as
``test_inventory_specs`` says). A change to any spec then fails ``test_every_spec_is_pinned``
naming the class, and says to bump the format.

The functions are the recipe of the package's docs (nothing of the guard is shipped by the
package; it is this repository's test). ``plain`` writes every mapping key as its own JSON, so
that a key of type ``int`` stays apart from the string of the same digits: ``canonical_json``
refuses a key that is not a string, and a bare ``str(k)`` would make the two alike and miss a
change of a key's type. Four of SI's specs have a polymorphic ``Parent.types`` keyed by ``int``
(``InflatonTrajectory``'s ``potential``; the ``diffusion_model`` of ``FullInstanton``,
``SlowRollInstanton`` and ``GradientCoupledInstanton``), so the conversion is needed for SI's own
digests; ``test_a_key_keeps_its_type`` guards it with stand-in ``Parent`` objects, as the siblings'
tests do.

Under DatastoreKit v0.5.0 ``InventorySpec`` has a seventh field, ``extra_values``. ``plain`` leaves
it out when it is empty, so that a spec declaring no extra table is what it was before the field
(P5); only ``GradientCoupledInstanton`` declares one. ``test_the_amendment`` pins the condition.

Nothing is opened: no store, nothing under ``var/``, no Ray.
"""

import dataclasses
import hashlib
import json
from collections.abc import Mapping

from datastorekit.store_inventory import InventorySpec, Parent, canonical_json, inventory_specs

from config.datastore import factories
from config.fingerprint import FINGERPRINT_FORMAT, SPEC_DIGESTS


def plain(value):
    """A spec as JSON: dataclasses as objects, sequences as lists, and every mapping key as the
    JSON of the key, so that 0 (``0``) and "0" (``"0"``) stay apart. An empty ``extra_values`` is
    left out, so that a spec declaring no extra table is what it was before the field."""
    if dataclasses.is_dataclass(value):
        return {
            f.name: plain(getattr(value, f.name))
            for f in dataclasses.fields(value)
            if not (f.name == "extra_values" and len(getattr(value, f.name)) == 0)
        }
    if isinstance(value, Mapping):
        return {json.dumps(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def _digest(spec) -> str:
    return hashlib.sha256(canonical_json(plain(spec)).encode()).hexdigest()


def spec_digests(factories) -> list:
    """[class, SHA-256 of its spec's canonical JSON] for each spec, in registry order (the order
    of ``inventory_specs``, which is the registry's)."""
    return [[name, _digest(spec)] for name, spec in inventory_specs(factories).items()]


def test_a_pin_exists_for_the_current_format():
    assert FINGERPRINT_FORMAT in SPEC_DIGESTS, (
        f"FINGERPRINT_FORMAT is {FINGERPRINT_FORMAT} but config.fingerprint.SPEC_DIGESTS has no "
        f"pin for it (it has {sorted(SPEC_DIGESTS)}): the format was bumped without a pin. "
        "Generate one with spec_digests(factories) from this module and add it beside the old "
        "ones, never over them, with a new golden file."
    )


def test_every_spec_is_pinned_for_the_current_format():
    assert FINGERPRINT_FORMAT in SPEC_DIGESTS, "no pin for the current format"
    pinned = SPEC_DIGESTS[FINGERPRINT_FORMAT]
    current = spec_digests(factories)
    if current == pinned:
        return
    pinned_by_name = dict(pinned)
    current_by_name = dict(current)
    changed = [
        n for n in current_by_name if n in pinned_by_name and current_by_name[n] != pinned_by_name[n]
    ]
    added = [n for n in current_by_name if n not in pinned_by_name]
    removed = [n for n in pinned_by_name if n not in current_by_name]
    lines = [f"the inventory specs no longer match the pin for format {FINGERPRINT_FORMAT}:"]
    lines += [f"  spec changed: {n}" for n in changed]
    lines += [f"  class added to the registry with a spec: {n}" for n in added]
    lines += [f"  class removed from the registry or its spec: {n}" for n in removed]
    if not (changed or added or removed):
        lines.append("  the classes and digests agree, but the registry order differs")
    lines.append(
        "A spec changed, so bump FINGERPRINT_FORMAT in config/fingerprint.py and add a new pin "
        "to SPEC_DIGESTS and a new golden file beside the old ones, never over them."
    )
    raise AssertionError("\n".join(lines))


def test_the_pin_has_one_pair_per_class_with_a_spec():
    """24 pairs: one per registered class with a spec, the count of ``test_inventory_specs``
    (22 definitions serve 24 classes). The names are ``inventory_specs``' in registry order."""
    pinned = SPEC_DIGESTS[FINGERPRINT_FORMAT]
    assert len(pinned) == 24
    assert [n for n, _ in pinned] == list(inventory_specs(factories))


def test_a_key_keeps_its_type():
    assert plain({0: "a"}) != plain({"0": "a"})
    assert canonical_json(plain({0: "a"})) != canonical_json(plain({"0": "a"}))

    by_int = Parent("x_serial", type_column="x_type", types={0: "Foo"})
    by_str = Parent("x_serial", type_column="x_type", types={"0": "Foo"})
    assert _digest(by_int) != _digest(by_str)


def test_the_amendment():
    """An empty ``extra_values`` is left out of ``plain``'s output; a non-empty one is not."""
    base = InventorySpec(leaves=("a",))
    assert base.extra_values == {}
    assert "extra_values" not in plain(base)
    # the same spec with the field removed from plain's output, written out by hand
    by_hand = {
        f.name: plain(getattr(base, f.name))
        for f in dataclasses.fields(base)
        if f.name != "extra_values"
    }
    assert plain(base) == by_hand
    assert _digest(base) == hashlib.sha256(canonical_json(by_hand).encode()).hexdigest()

    with_extra = dataclasses.replace(base, extra_values={"FooValue": "foo_serial"})
    assert "extra_values" in plain(with_extra)
    assert _digest(with_extra) != _digest(base)
