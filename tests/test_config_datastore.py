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

"""config.datastore's three objects, against SI's old layer's at prompt 05's gate.

The literals below were captured from SI's own layer (its ``Datastore/SQL/Datastore.py`` and
``Datastore/SQL/ClientPool.py``) at the gate of prompt 05 of the ``dk-and-rpk-migration``
campaign, before the data moved, by a script that read the layer and not
``config.datastore``. They are written out, not computed from the module under test, so that
an entry dropped, reordered, retyped or resized in ``config/datastore.py`` fails here.

Prompt 09 deleted that layer: the pool is the ``datastorekit`` package's, and every pool
construction is given ``config.datastore``'s registry and batch sizes, which an ``ast`` test
below pins. With the layer gone, ``config.datastore`` imports on its own in a fresh process
(the circular import through ``Datastore/SQL/__init__.py`` that once made it wait for the
layer is gone), which the last test checks.
"""

import ast
import importlib
import os
import subprocess
import sys
from pathlib import Path

_config = importlib.import_module("config.datastore")

_ROOT = Path(__file__).resolve().parent.parent

# (table name, factory class, class held by a quantity factory, else None), in order.
_REGISTRY = [
    ("version", "sqla_version_factory", None),
    ("store_tag", "sqla_store_tag_factory", None),
    ("redshift", "sqla_redshift_factory", None),
    ("tolerance", "sqla_tolerance_factory", None),
    ("efold_value", "sqla_efold_factory", None),
    ("delta_Nstar", "sqla_delta_Nstar_factory", None),
    ("N_init", "sqla_N_init_factory", None),
    ("N_final", "sqla_N_final_factory", None),
    ("n_collocation_points", "sqla_n_collocation_points_factory", None),
    ("alpha_regularization", "sqla_alpha_regularization_factory", None),
    ("inflaton_mass", "sqla_dimensionful_quantity_factory", "inflaton_mass"),
    ("quartic_coupling", "sqla_dimensionless_quantity_factory", "quartic_coupling"),
    ("phi_value", "sqla_dimensionful_quantity_factory", "phi_value"),
    ("pi_value", "sqla_dimensionful_quantity_factory", "pi_value"),
    ("QuadraticPotential", "sqla_QuadraticPotential_factory", None),
    ("QuarticPotential", "sqla_QuarticPotential_factory", None),
    ("MasslessDecoupledDiffusion", "sqla_MasslessDecoupledDiffusion_factory", None),
    ("IntegrationSolver", "sqla_IntegrationSolver_factory", None),
    ("InflatonTrajectory", "sqla_InflatonTrajectory_factory", None),
    ("InflatonTrajectoryValue", "sqla_InflatonTrajectoryValue_factory", None),
    ("CosmologicalParams", "sqla_cosmological_params_factory", None),
    ("FullInstanton", "sqla_FullInstantonFactory", None),
    ("FullInstantonValue", "sqla_FullInstantonValue_factory", None),
    ("GradientCoupledInstanton", "sqla_GradientCoupledInstantonFactory", None),
    (
        "GradientCoupledInstantonValue",
        "sqla_GradientCoupledInstantonValue_factory",
        None,
    ),
    (
        "GradientCoupledInstantonProfile",
        "sqla_GradientCoupledInstantonProfileFactory",
        None,
    ),
    ("SlowRollInstanton", "sqla_SlowRollInstantonFactory", None),
    ("SlowRollInstantonValue", "sqla_SlowRollInstantonValue_factory", None),
    ("CompactionFunction", "sqla_CompactionFunctionFactory", None),
    ("CompactionFunctionSamples", "sqla_CompactionFunctionSamplesFactory", None),
]

_DROP_GROUPS = [
    ("inflaton-trajectory", ["InflatonTrajectoryValue", "InflatonTrajectory"]),
    ("full-instanton", ["FullInstantonValue", "FullInstanton"]),
    ("slow-roll-instanton", ["SlowRollInstantonValue", "SlowRollInstanton"]),
    ("compaction-function", ["CompactionFunctionSamples", "CompactionFunction"]),
    (
        "gradient-coupled-instanton",
        [
            "GradientCoupledInstantonValue",
            "GradientCoupledInstantonProfile",
            "GradientCoupledInstanton",
        ],
    ),
]

_BATCH_SIZES = [
    ("store_tag", 5),
    ("redshift", 200),
    ("tolerance", 5),
    ("temperature", 200),
    ("phi_value", 200),
    ("pi_value", 200),
    ("efold_value", 500),
    ("delta_Nstar", 10),
    ("N_init", 10),
    ("N_final", 10),
    ("n_collocation_points", 5),
    ("alpha_regularization", 5),
    ("inflaton_mass", 10),
    ("quartic_coupling", 10),
    ("QuadraticPotential", 10),
    ("QuarticPotential", 10),
    ("InflatonTrajectory", 20),
    ("MasslessDecoupledDiffusion", 5),
    ("FullInstanton", 20),
    ("FullInstantonValue", 500),
    ("GradientCoupledInstanton", 20),
    ("GradientCoupledInstantonValue", 500),
    ("GradientCoupledInstantonProfile", 500),
    ("SlowRollInstanton", 20),
    ("SlowRollInstantonValue", 500),
    ("CosmologicalParams", 5),
    ("CompactionFunction", 20),
    ("CompactionFunctionSamples", 500),
    ("IntegrationSolver", 6),
]


def test_factories_registry_as_captured():
    registry = [
        (
            name,
            type(factory).__name__,
            factory.ObjectType.__name__
            if type(factory).__name__
            in (
                "sqla_dimensionful_quantity_factory",
                "sqla_dimensionless_quantity_factory",
            )
            else None,
        )
        for name, factory in _config.factories.items()
    ]
    assert len(registry) == 30
    assert registry == _REGISTRY


def test_drop_groups_as_captured():
    assert len(_config.drop_groups) == 5
    assert [(k, list(v)) for k, v in _config.drop_groups.items()] == _DROP_GROUPS


def test_serial_batch_sizes_as_captured():
    assert len(_config.serial_batch_sizes) == 29
    assert list(_config.serial_batch_sizes.items()) == _BATCH_SIZES


def test_batch_sizes_per_table():
    """A failure names the table whose size moved."""
    expected = dict(_BATCH_SIZES)
    for table, size in _config.serial_batch_sizes.items():
        assert expected.get(table) == size, (
            f"{table}: {size} (captured {expected.get(table)})"
        )
    assert set(_config.serial_batch_sizes) == set(expected)


# The four ShardedPool constructions: the two drivers' and the plot scripts', and live_pool's.
_POOL_FILES = [
    "main.py",
    "plot_GradientCoupledSolutions.py",
    "plot_InstantonSolutions.py",
    "tests/conftest.py",
]


def _config_datastore_names(tree):
    """{local name: name in config.datastore} for each ``from config.datastore import ...``."""
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "config.datastore":
            for alias in node.names:
                names[alias.asname or alias.name] = alias.name
    return names


def _named(value, imported):
    """What config.datastore object an argument names: an imported name, or the dotted
    ``config.datastore.<name>``; else None."""
    if isinstance(value, ast.Name):
        return imported.get(value.id)
    if (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Attribute)
        and isinstance(value.value.value, ast.Name)
        and value.value.value.id == "config"
        and value.value.attr == "datastore"
    ):
        return value.attr
    return None


def test_every_pool_construction_passes_config_datastore():
    """Each of the four files constructs one ShardedPool, by keyword ``factories=`` and
    ``serial_batch_sizes=`` naming config.datastore's two objects, and passes neither of the
    old layer's ``drop_actions=`` and ``inventory_config=``. A failure names the file and line."""
    problems = []
    for rel in _POOL_FILES:
        tree = ast.parse((_ROOT / rel).read_text(), filename=rel)
        imported = _config_datastore_names(tree)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "ShardedPool")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "ShardedPool")
            )
        ]
        if len(calls) != 1:
            problems.append(f"{rel}: {len(calls)} ShardedPool(...) calls, expected 1")
            continue
        (call,) = calls
        where = f"{rel}:{call.lineno}"
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}
        for name in ("factories", "serial_batch_sizes"):
            if name not in keywords:
                problems.append(f"{where}: no {name}=")
            elif _named(keywords[name], imported) != name:
                problems.append(f"{where}: {name}= does not name config.datastore.{name}")
        for name in ("drop_actions", "inventory_config"):
            if name in keywords:
                problems.append(f"{where}: passes {name}=")
        if any(kw.arg is None for kw in call.keywords):
            problems.append(f"{where}: passes **kwargs")
    assert not problems, "\n".join(problems)


def test_importing_the_data_starts_no_ray():
    """In a fresh process, so the answer does not depend on test order. config.datastore is
    imported alone, first: the closing test of
    ``[config-datastore-cannot-be-imported-before-the-layer]`` (dk-and-rpk-migration prompt 09)."""
    code = (
        "import importlib; "
        "importlib.import_module('config.datastore'); "
        "import ray; "
        "assert not ray.is_initialized(); print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(_ROOT)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
