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

"""
The run registry's configuration (rrk-adoption prompt 01, items C2-C5).

What this pins, and why:
- `runregistrykit.toml` gives the roots `var/runs` and `var/datastores` (README R6) and the
  distributions every run's manifest records. They must be `utilities.RECORDED_DISTRIBUTIONS`,
  the ones each driver prints on its `>> packages:` line (R3), so that a run's log and its
  manifest name the same packages. The test compares the two lists rather than naming the
  packages: a package added to one list and not the other fails here. The package rejects an unknown key, but a misspelt key it does know of cannot be told from a
  deliberate one, so the test holds the exact set of keys: prompt 02 extends `EXPECTED_KEYS` with
  `stores` and nothing else may be added unnoticed.
- `var/` is ignored by git, so that neither the runs nor the registered stores can be committed,
  and `git clean -x` is the only thing that can delete them (`.claude/rules/run-registry.md`).
- RunRegistryKit is installed from its `v0.2.0` tag and not editable: the check
  `tests/test_package_provenance.py` makes for the other two packages.
- `.claude/settings.json` holds the `SessionStart` discovery hook (U1).

No Ray, no store. Nothing is written. Under 1 s.
"""

import json
import pathlib
import subprocess
import tomllib

import pytest

import runregistrykit

import utilities

ROOT = pathlib.Path(__file__).resolve().parent.parent

EXPECTED_KEYS = {"runs_root", "stores_root", "distributions", "stores"}


def test_client_root_gives_the_roots_and_distributions():
    client = runregistrykit.find_client_root(client_root=str(ROOT))
    assert pathlib.Path(client.root) == ROOT
    assert pathlib.Path(client.runs_root) == ROOT / "var" / "runs"
    assert pathlib.Path(client.stores_root) == ROOT / "var" / "datastores"
    assert client.distributions == utilities.RECORDED_DISTRIBUTIONS


def test_config_holds_exactly_the_expected_keys():
    with open(ROOT / "runregistrykit.toml", "rb") as f:
        config = tomllib.load(f)
    assert set(config) == EXPECTED_KEYS


@pytest.mark.parametrize("path", ["var/runs/x", "var/datastores/x.sqlite"])
def test_var_is_ignored_by_git(path):
    # `git check-ignore -q` accepts one path only, so each is checked in turn.
    result = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT)
    assert result.returncode == 0


def test_runregistrykit_is_installed_from_the_v0_2_0_tag():
    provenance = runregistrykit.package_provenance(("runregistrykit",))["runregistrykit"]
    assert provenance is not None
    assert provenance["version"] == "0.2.0"
    assert provenance["url"] == "https://github.com/ds283/RunRegistryKit"
    assert provenance["commit"].startswith("0bae3a3")
    assert provenance["requested_revision"] == "v0.2.0"
    assert provenance["editable"] is False


def test_session_start_hook_runs_the_discovery_command():
    with open(ROOT / ".claude" / "settings.json") as f:
        settings = json.load(f)
    groups = settings["hooks"]["SessionStart"]
    commands = [h["command"] for g in groups for h in g["hooks"] if h["type"] == "command"]
    assert any("runregistrykit list" in c for c in commands)
