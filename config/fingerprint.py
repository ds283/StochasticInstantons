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

"""The store fingerprint's client side (rrk-adoption prompt 02, items F1-F4; campaign README §0.3
and §6.2, P5, P6 and P11).

A store's fingerprint is split by layer. **What goes into it** is this repository's: the
``inventory_spec()`` of each factory, the registry of factories in ``config.datastore``, and the
format number below. **How that content is encoded and digested** is DatastoreKit's
(``datastorekit.store_fingerprint``), versioned there by its own ``ENCODING_FORMAT`` and recorded
beside the digest as ``encoding_format``. **When a fingerprint is taken and where it is recorded**
is RunRegistryKit's (``runregistrykit.stores``), which is handed the fingerprinter below and treats
what it returns as opaque. This module is where this repository keeps its part, so that the format
number sits beside the thing it versions.

- ``FINGERPRINT_FORMAT``: this repository's fingerprint format, with its history.
- ``SPEC_DIGESTS``: the pin of every inventory spec's digest for each format, which
  ``tests/test_fingerprint_format_guard.py`` checks.
- ``fingerprinter``: a ``runregistrykit.fingerprint.DatastoreKitFingerprinter`` over
  ``config.datastore.factories`` at ``FINGERPRINT_FORMAT``. ``runregistrykit.toml`` at the
  repository root names it (``[stores] fingerprinter = "config.fingerprint:fingerprinter"``), and
  every ``runregistrykit`` store operation loads it from there. It is an instance, as the loader
  requires.

Importing this module adds RunRegistryKit's own modules (``runregistrykit``,
``runregistrykit.client`` and ``runregistrykit.fingerprint``) and the standard-library modules they
need (``getpass``, ``termios`` and ``tomllib``), and nothing of Ray, SQLAlchemy or DatastoreKit
beyond what ``config.datastore`` loads: ``DatastoreKitFingerprinter`` imports DatastoreKit only
inside its methods.
"""

from runregistrykit.fingerprint import DatastoreKitFingerprinter

from config.datastore import factories

# The fingerprint's format. A fingerprint is compared only with one of the same format. The number
# moves when what the inventory records changes: a change to any factory's ``inventory_spec()``, or
# to the registry's classes or their order. It moves in the commit that makes that change, with a
# new pin in SPEC_DIGESTS and a new golden file beside the old ones and never over them
# (``tests/data/store_fingerprint_*.json``; ``test_store_fingerprint_golden.GOLDEN`` names the
# current one). The encoding and the digest are DatastoreKit's, versioned by its
# ``ENCODING_FORMAT``; a change there does not bump this number.
#
# Format 1: rrk-adoption prompt 02, the first of a history. The specs are those of
# dk-and-rpk-migration prompt 10b, on DatastoreKit v0.5.0.
FINGERPRINT_FORMAT = 1

# The spec pin (campaign README P5; RunRegistryKit's docs/adoption/README.md §6, "The Q5 guard",
# and its addendum for DatastoreKit v0.5.0). For each format that has a pin: [class, SHA-256] for
# every class of the registry whose factory declares an ``inventory_spec()``, in registry order,
# each digest that of the spec's canonical JSON, as computed by ``spec_digests`` in
# ``tests/test_fingerprint_format_guard.py``, which fails naming any class whose digest differs.
# Format 1 has 24 pairs, one per registered class with a spec (22 definitions serve them), and 18
# distinct digests.
SPEC_DIGESTS = {
    1: [
        [
            "version",
            "02929e9353a2d7ed737e0c5336dd29b1bc64bf84693f865600ba6c66f455ec10",
        ],
        [
            "store_tag",
            "02929e9353a2d7ed737e0c5336dd29b1bc64bf84693f865600ba6c66f455ec10",
        ],
        [
            "redshift",
            "3e69e5a912303825acefccda1d940e339b9c295f1546be999265b5b63af82ffb",
        ],
        [
            "tolerance",
            "38ff5e8bf9db7d5594c3f35c38dba28114a5661a284645cc875c4f0f93a7a55f",
        ],
        [
            "efold_value",
            "8a2a81c48a36ba599dccfeef72d52bd20f2ac35425f0d96771d2e402adb4d89e",
        ],
        [
            "delta_Nstar",
            "c098757d4b33da64a449820f7f13c2c04112d2d319a0501ef31b184a9dc93a4a",
        ],
        [
            "N_init",
            "c098757d4b33da64a449820f7f13c2c04112d2d319a0501ef31b184a9dc93a4a",
        ],
        [
            "N_final",
            "c098757d4b33da64a449820f7f13c2c04112d2d319a0501ef31b184a9dc93a4a",
        ],
        [
            "n_collocation_points",
            "f7933ac8f3ff30c47ced22fb4b74602fc284c9fb97a9c7d69a22e8b451da0015",
        ],
        [
            "alpha_regularization",
            "ab3e39f9b16ab36a0aba3f8337139980504c9451599b24e625bd712643aa4689",
        ],
        [
            "inflaton_mass",
            "9e45a84f17fbc77aab1013efe1901f7024986dc8e8ab9d502156ab8e64472cca",
        ],
        [
            "quartic_coupling",
            "c098757d4b33da64a449820f7f13c2c04112d2d319a0501ef31b184a9dc93a4a",
        ],
        [
            "phi_value",
            "9e45a84f17fbc77aab1013efe1901f7024986dc8e8ab9d502156ab8e64472cca",
        ],
        [
            "pi_value",
            "9e45a84f17fbc77aab1013efe1901f7024986dc8e8ab9d502156ab8e64472cca",
        ],
        [
            "QuadraticPotential",
            "3683df162cb28798e6d7fe2964ac80dc0f8b9c777ed6d1fe0472fe6eb1f51742",
        ],
        [
            "QuarticPotential",
            "fa01af37c91610d05b6b1b632a95148dadedb343314254704dac459425695af6",
        ],
        [
            "MasslessDecoupledDiffusion",
            "aabd79b23269bdaa357ace82550ba6e4e38343e4ff3f4031108cc5500a2786b6",
        ],
        [
            "IntegrationSolver",
            "6b7d69e652c00050e30d75431c082d6b984460925f3280d16ca636e2b843c402",
        ],
        [
            "InflatonTrajectory",
            "d69805c01c14adca197efcbe1368e8914c9f674e662e814b32cc269f76f36057",
        ],
        [
            "CosmologicalParams",
            "14f706b25e7fbbb8b23eb67937d9c62a4ff2a4b2fb3c4e57d2950863069a3c04",
        ],
        [
            "FullInstanton",
            "208308f8b9f800a7e81d1e27cc746a2c24446aa15168b1e1b57c840b0adda9cc",
        ],
        [
            "GradientCoupledInstanton",
            "0059b6b6e4dbef96d94e25eb9490f1b777f2b594bdc86e4a596f2096aa87a9f0",
        ],
        [
            "SlowRollInstanton",
            "9ba0ef732402283a6e86e0ad5f65e0be41d2be7b3ac57d35e283dfd7c8f26521",
        ],
        [
            "CompactionFunction",
            "33e791dfa1be62fb80ed5f9e168fae7fc00c9fcf39f392196696801446e08317",
        ],
    ],
}

fingerprinter = DatastoreKitFingerprinter(factories, FINGERPRINT_FORMAT)
