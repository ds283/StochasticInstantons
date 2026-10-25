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

"""The fingerprint a registered run takes once its program has returned (rrk-adoption prompt 03,
W5 and W6 test 5; campaign README P11).

The store is rrk-adoption 02's golden store, built as 02's golden test builds it: ``_STORE_SCRIPT``
and the module-scoped ``store`` fixture are imported from ``tests/test_inventory_store.py``,
unmodified, so this module builds it once, in a subprocess under that script's private Ray, in a
``tempfile`` directory, closed before it is read. Its fingerprint is the golden file's
(``tests/test_store_fingerprint_golden.GOLDEN``). One store cannot serve both tests, since the
sidecar of the first is left beside it, so each test copies the store's directory into its own
``tmp_path`` and runs there (the orchestrator's note for 03, correction 9: a copy fingerprints to
the golden digest). With a sidecar, it is made by ``runregistrykit.stores.create_sidecar`` before
the run, as a person makes one after a first close.

The wrapper's ``main`` runs in this process on a stand-in that returns without touching the store,
with ``ray.init`` and ``ray.shutdown`` replaced by stand-ins (``registered_run_helpers.in_process``),
into a runs root in the same temporary directory. ``integration``: the store needs a private Ray,
in its own subprocess; this process never initialises one. Nothing under ``var/`` is read or
written.
"""

import json
import shutil
from pathlib import Path

import pytest
from runregistrykit.stores import create_sidecar, sidecar_path

from registered_run_helpers import (  # noqa: F401
    REPO_ROOT,
    in_process,
    no_ray_at_the_end,
    only_run,
    read_json,
    standin_program,
    wrapper_argv,
)

# the golden store's builder and fixture, unmodified (P6); ``store`` is the module-scoped fixture
from test_inventory_store import _STORE_SCRIPT, store  # noqa: F401
from test_store_fingerprint_golden import GOLDEN, without_taken

pytestmark = pytest.mark.integration


class Copy:
    """The golden store's directory, copied into this test's own ``tmp_path``."""

    def __init__(self, store, tmp_path):
        self.top = Path(tmp_path).resolve()
        directory = self.top / "store"
        shutil.copytree(Path(store).parent, directory)
        self.primary = directory / Path(store).name
        self.runs_root = self.top / "runs"
        self.runs_root.mkdir()
        self.golden = json.loads(GOLDEN.read_text())

    def a_run(self, request):
        program = standin_program(self.top, "return", self.runs_root)
        done = in_process(
            request.addfinalizer,
            program,
            wrapper_argv(self.primary, slug="golden"),
            self.runs_root,
        )
        assert done.outcome is None, repr(done.outcome)
        return read_json(only_run(self.runs_root) / "status.json")


@pytest.fixture
def copy(store, tmp_path):
    return Copy(store, tmp_path)


def test_with_a_sidecar_the_golden_fingerprint_is_written_to_it(copy, request):
    create_sidecar(
        copy.primary,
        purpose="the golden store of rrk-adoption 02, in a test of the wrapper",
        client_root=str(REPO_ROOT),
    )
    status = copy.a_run(request)
    assert (status["state"], status["exit_code"]) == ("done", 0)
    assert status["fingerprint_sidecar"] == "written"
    assert "fingerprint_error" not in status
    assert status["fingerprint"]["digest"] == copy.golden["digest"]
    assert without_taken(status["fingerprint"]) == without_taken(copy.golden)
    sidecar = read_json(sidecar_path(copy.primary))
    assert sidecar["fingerprint"]["digest"] == copy.golden["digest"]


def test_without_one_it_is_not_written_and_the_run_is_still_done(copy, request):
    files_before = sorted(p.name for p in copy.primary.parent.iterdir())
    status = copy.a_run(request)
    assert (status["state"], status["exit_code"]) == ("done", 0)
    # the text after "not written" is the package's (runregistrykit/__init__.py:865-868)
    assert status["fingerprint_sidecar"].startswith("not written"), status[
        "fingerprint_sidecar"
    ]
    assert "(there is none)" in status["fingerprint_sidecar"]
    assert "fingerprint_error" not in status
    assert status["fingerprint"]["digest"] == copy.golden["digest"]
    assert not sidecar_path(copy.primary).exists()
    assert sorted(p.name for p in copy.primary.parent.iterdir()) == files_before
