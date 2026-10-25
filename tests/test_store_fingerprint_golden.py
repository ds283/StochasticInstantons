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

"""This repository's golden store fingerprint, and the module that takes it (rrk-adoption prompt 02,
item F4; campaign README §0.3 and §6.2, P6 and P11).

What goes into a fingerprint is this repository's: the factories' inventory specs, the registry in
``config.datastore`` and the format number in ``config.fingerprint``. How it is encoded and digested
is DatastoreKit's (``datastorekit.store_fingerprint``), and when and where it is taken is
RunRegistryKit's, through the fingerprinter ``config.fingerprint`` holds and ``runregistrykit.toml``
names.

- ``TestGolden`` (``integration``): the fingerprint of the golden store is the committed golden file
  ``GOLDEN``.
- ``TestConfigFingerprint``: ``config/fingerprint.py`` and the config's naming of it. It needs no
  store and no Ray, so it is in the default selection (the class is marked, not the module).
- ``TestCommandLine`` (``integration``): ``python -m runregistrykit store fingerprint``, once, by
  subprocess, on that store.

**The golden store** is the one ``tests/test_inventory_store.py`` builds: ``_STORE_SCRIPT`` and its
``store`` fixture are imported from that module, unmodified (P6). It is a two-shard store of
synthetic rows (a row of every class but store_tag, redshift and
IntegrationSolver), written through the package's pool in a subprocess under a
private Ray and closed before it is read, in a ``tempfile`` directory. The fixture is module-scoped,
so this module builds the store once, for itself. Its rows must not change while the golden file
stands: a change to ``_STORE_SCRIPT`` that moves a value a spec reads moves the fingerprint, and
fails ``TestGolden``.

**The golden file** is under ``data/``, written once and never overwritten. It was written from
``config.fingerprint.fingerprinter.take(primary, None)`` as
``json.dumps(fp, indent=2, sort_keys=True) + "\\n"``, so its ``taken`` is ``null``; the tests take
with ``taken={}`` and compare with ``taken`` removed. **A later format adds a file beside it**,
named for the prompt that changed the format (``store_fingerprint_<campaign>-<prompt>.json``), in
the same commit that bumps ``config.fingerprint.FINGERPRINT_FORMAT`` and adds its pin, and
``GOLDEN`` is pointed at the new file; the old file stays, so that the history of formats is the
history of the files.

Nothing under ``var/`` is opened or created.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from datastorekit.store_fingerprint import ENCODING_FORMAT
from datastorekit.store_inventory import read_inventory
from runregistrykit import find_client_root
from runregistrykit.fingerprint import (
    DatastoreKitFingerprinter,
    Fingerprinter,
    load_fingerprinter,
)

import config.datastore
import config.fingerprint
from config.fingerprint import FINGERPRINT_FORMAT

# the golden store's builder and fixture, unmodified (P6); ``store`` is the module-scoped fixture
from test_inventory_store import _STORE_SCRIPT, store  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "data" / "store_fingerprint_rrk-adoption-02.json"


def without_taken(fingerprint) -> dict:
    out = dict(fingerprint)
    out.pop("taken", None)
    return out


@pytest.mark.integration
class TestGolden:
    """The fingerprint of the golden store is the committed golden file."""

    def test_the_store_reads_with_no_problem_and_every_class(self, store):
        inventory = read_inventory(store, config.datastore.factories)
        assert inventory.problems == ()
        assert len(inventory.classes) == 24
        # the harness writes a row of every class but these three (its EXPECTED_COUNTS)
        empty = {name for name, entry in inventory.classes.items() if entry.count == 0}
        assert empty == {"store_tag", "redshift", "IntegrationSolver"}

    def test_the_golden_fingerprint(self, store):
        golden = json.loads(GOLDEN.read_text())
        assert golden["fingerprint_format"] == FINGERPRINT_FORMAT
        assert golden["encoding_format"] == ENCODING_FORMAT
        assert golden["taken"] is None
        assert golden["problems"] == {}

        fp, _ = config.fingerprint.fingerprinter.take(store, {})
        assert fp["problems"] == {}
        assert fp["taken"] == {}
        assert without_taken(fp) == without_taken(golden)


class TestConfigFingerprint:
    """``config/fingerprint.py``, and ``runregistrykit.toml``'s naming of its fingerprinter."""

    def test_the_config_names_the_fingerprinter(self):
        client = find_client_root(client_root=REPO_ROOT)
        # the loader refuses (with a ConfigError) a config that names a class, or nothing
        loaded = load_fingerprinter(client)
        assert loaded is config.fingerprint.fingerprinter
        assert isinstance(loaded, DatastoreKitFingerprinter)
        assert isinstance(loaded, Fingerprinter)
        assert loaded.fingerprint_format == FINGERPRINT_FORMAT
        assert loaded.factories is config.datastore.factories


@pytest.mark.integration
class TestCommandLine:
    """``python -m runregistrykit store fingerprint``, once, on the golden store, which has no
    sidecar: it prints the golden digest and exits 0, with nothing recorded."""

    def test_store_fingerprint(self, store, tmp_path):
        golden = json.loads(GOLDEN.read_text())
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        var = REPO_ROOT / "var"
        var_before = sorted(p.name for p in var.rglob("*")) if var.exists() else None
        store_before = sorted(p.name for p in store.parent.iterdir())

        argv = [
            sys.executable,
            "-m",
            "runregistrykit",
            "--client-root",
            str(REPO_ROOT),
            "store",
            "fingerprint",
            str(store),
            "--runs-root",
            str(runs_root),
        ]
        env = dict(os.environ)
        env.pop("RAY_ADDRESS", None)
        done = subprocess.run(
            argv, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=300
        )
        assert done.returncode == 0, done.stdout + done.stderr
        lines = done.stdout.splitlines()
        # the command pads its labels into columns
        squeezed = [" ".join(line.split()) for line in lines]
        assert f"digest: {golden['digest']}" in squeezed
        assert f"format: {golden['fingerprint_format']}" in squeezed
        assert lines[-1].strip() == "recorded: none recorded (the sidecar is absent)"

        # nothing was written beside the store, under the runs root or at the root
        assert sorted(p.name for p in store.parent.iterdir()) == store_before
        assert list(runs_root.iterdir()) == []
        var_after = sorted(p.name for p in var.rglob("*")) if var.exists() else None
        assert var_after == var_before
