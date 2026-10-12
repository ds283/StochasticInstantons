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

import importlib.metadata
import json
import time
from itertools import zip_longest
from math import fabs, log
from traceback import print_tb

from Units.base import UnitsLike


class WallclockTimer:
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time

        if exc_type is not None:
            print(f"type={exc_type}, value={exc_val}")
            print_tb(exc_tb)


SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR


def format_time(interval: float) -> str:
    int_interval = int(interval)
    str = ""

    if int_interval > SECONDS_PER_DAY:
        days = int_interval // SECONDS_PER_DAY
        int_interval = int_interval - days * SECONDS_PER_DAY
        interval = interval - days * SECONDS_PER_DAY
        if len(str) > 0:
            str = str + f" {days}d"
        else:
            str = f"{days}d"

    if int_interval > SECONDS_PER_HOUR:
        hours = int_interval // SECONDS_PER_HOUR
        int_interval = int_interval - hours * SECONDS_PER_HOUR
        interval = interval - hours * SECONDS_PER_HOUR
        if len(str) > 0:
            str = str + f" {hours}h"
        else:
            str = f"{hours}h"

    if int_interval > SECONDS_PER_MINUTE:
        minutes = int_interval // SECONDS_PER_MINUTE
        int_interval = int_interval - minutes * SECONDS_PER_MINUTE
        interval = interval - minutes * SECONDS_PER_MINUTE
        if len(str) > 0:
            str = str + f" {minutes}m"
        else:
            str = f"{minutes}m"

    if len(str) > 0:
        str = str + f" {interval:.3g}s"
    else:
        str = f"{interval:.3g}s"

    return str


def format_energy(
    value, units: UnitsLike, format_string: str = ".5g", include_space=True
) -> str:
    _value_as_float: float
    if isinstance(value, float):
        _value_as_float = value
    elif hasattr(value, "as_float"):
        _value_as_float = value.as_float
    else:
        # allow an exception to be raised if conversion is not possible
        _value_as_float = float(value)

    config = {
        "eV": {
            "unit": units.eV,
        },
        "keV": {
            "unit": units.keV,
        },
        "MeV": {
            "unit": units.MeV,
        },
        "GeV": {
            "unit": units.GeV,
        },
        "Mp": {"unit": units.PlanckMass},
    }

    # the unit that produces a result closest to one gives |log| closest to zero
    trials = {
        label: fabs(log(fabs(_value_as_float / data["unit"])))
        for label, data in config.items()
    }

    # search for minimum value
    best_label = min(trials, key=trials.get)

    # format value using this unit and return
    return f"{_value_as_float/config[best_label]['unit']:{format_string}}{' ' if include_space else ''}{best_label}"


class energy_formatter:
    def __init__(
        self, units: UnitsLike, format_string=".5g", include_space: bool = True
    ):
        self._units: UnitsLike = units
        self._format_string: str = format_string
        self._include_space: bool = include_space

    def __call__(self, value) -> str:
        return format_energy(
            value,
            units=self._units,
            format_string=self._format_string,
            include_space=self._include_space,
        )


# grouper borrowed from itertools recipes
# https://docs.python.org/3/library/itertools.html#itertools-recipes
def grouper(iterable, n, *, incomplete="fill", fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks."
    # grouper('ABCDEFG', 3, fillvalue='x') → ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='strict') → ABC DEF ValueError
    # grouper('ABCDEFG', 3, incomplete='ignore') → ABC DEF
    iterators = [iter(iterable)] * n
    match incomplete:
        case "fill":
            return zip_longest(*iterators, fillvalue=fillvalue)
        case "strict":
            return zip(*iterators, strict=True)
        case "ignore":
            return zip(*iterators)
        case _:
            raise ValueError("Expected fill, strict, or ignore")


def to_float(val) -> float:
    """
    Safely convert a numpy float64, single-element array, or other numeric
    types to a native Python float.
    """
    if hasattr(val, "item"):
        return float(val.item())
    return float(val)


# The distributions whose installed release a driver records in its output (dk-and-rpk-migration
# prompt 01; README P5): the two packages that campaign adopts. From the RayPoolKit swap on, a run
# executes code that is not in this repository's tree, so its log says which release ran.
RECORDED_DISTRIBUTIONS = ("datastorekit", "raypoolkit")


def installed_package_provenance(names=RECORDED_DISTRIBUTIONS) -> dict:
    """
    What is installed of each named distribution, read from its metadata.

    Maps each name to `None` when the distribution is not installed, and otherwise to a dict with
    exactly these keys:
    - `version`: the installed distribution's version;
    - `url`: `url` in the distribution's PEP 610 `direct_url.json`, or `None`;
    - `commit`: its `vcs_info.commit_id`, or `None`;
    - `requested_revision`: its `vcs_info.requested_revision` (the tag or branch asked for), or
      `None`;
    - `editable`: `True` when `dir_info.editable` is the boolean `true`, and `False` otherwise.

    These are the fields, with the same meaning, of SecondaryGWKit's
    `RunRegistry.package_provenance()` and of ChamPBH's helper of this name, so that a later move
    to a shared registry is a substitution (README P5). Only the standard library is used, and no
    package being described is imported. An absent, unreadable or malformed `direct_url.json` (one
    that is not a JSON object), or a `vcs_info` or `dir_info` that is not an object, gives `None`
    for the three fields it would have supplied and `False` for `editable`. It never raises on odd
    metadata, and it never refuses an install: an editable one is recorded as such.
    """
    packages = {}
    for name in names:
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
            continue

        try:
            origin = json.loads(distribution.read_text("direct_url.json"))
        except (TypeError, ValueError, OSError):
            # TypeError: no direct_url.json (read_text returned None); ValueError: not JSON, or
            # not UTF-8 (UnicodeDecodeError); OSError: present but unreadable
            origin = None
        if not isinstance(origin, dict):
            origin = {}

        vcs_info = origin.get("vcs_info")
        if not isinstance(vcs_info, dict):
            vcs_info = {}
        dir_info = origin.get("dir_info")
        if not isinstance(dir_info, dict):
            dir_info = {}

        packages[name] = {
            "version": distribution.version,
            "url": origin.get("url"),
            "commit": vcs_info.get("commit_id"),
            "requested_revision": vcs_info.get("requested_revision"),
            "editable": dir_info.get("editable") is True,
        }
    return packages


def format_package_provenance(provenance: dict) -> str:
    """
    One line saying what `installed_package_provenance()` found, for a driver to print. Worded as
    ChamPBH's, so that the clients' logs read alike. Each distribution is one of:
    - `NAME not installed`;
    - `NAME VERSION (URL@COMMIT, requested REVISION)` for a VCS install, the commit in full and
      the URL as pip recorded it (without a `git+` prefix);
    - `NAME VERSION (editable, URL)` for an editable install;
    - `NAME VERSION (no recorded origin)` for an install whose `direct_url.json` is absent or
      records nothing usable.
    They are joined by `; ` after the prefix `>> packages: `.
    """
    items = []
    for name, entry in provenance.items():
        if entry is None:
            items.append(f"{name} not installed")
            continue

        details = []
        if entry.get("editable"):
            details.append("editable")

        url = entry.get("url")
        commit = entry.get("commit")
        if url is not None and commit is not None:
            details.append(f"{url}@{commit}")
        elif url is not None:
            details.append(url)
        elif commit is not None:
            details.append(f"commit {commit}")

        revision = entry.get("requested_revision")
        if revision is not None:
            details.append(f"requested {revision}")

        if len(details) == 0:
            details.append("no recorded origin")

        items.append(f"{name} {entry.get('version')} ({', '.join(details)})")

    return ">> packages: " + "; ".join(items)
