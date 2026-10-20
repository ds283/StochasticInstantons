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

"""config.datastore's three objects, against the layer's at prompt 05's gate.

The literals below were captured from the layer (``Datastore.SQL.Datastore`` and
``Datastore.SQL.ClientPool``) at the gate of prompt 05 of the ``dk-and-rpk-migration``
campaign, before the data moved, by a script that read the layer and not
``config.datastore``. They are written out, not computed from the module under test, so that
an entry dropped, reordered, retyped or resized in ``config/datastore.py`` fails here.

The layer is imported first, with ``importlib``: until prompt 09 deletes the layer, importing
``config.datastore`` in a fresh process fails with a circular-import ``ImportError``
(``Datastore/SQL/__init__.py`` imports the layer, which imports ``config.datastore``, which
imports the factories inside that package). ``import Datastore.SQL.Datastore as m`` would
not do for the module, since the package attribute ``Datastore.SQL.Datastore`` is the actor.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

# Layer first, then config.datastore (see the module docstring).
_layer = importlib.import_module("Datastore.SQL.Datastore")
_client_pool = importlib.import_module("Datastore.SQL.ClientPool")
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


def test_layer_reads_the_data_from_config_datastore():
    assert _layer._factories is _config.factories
    assert _layer._drop_actions is _config.drop_groups
    assert _client_pool._default_serial_batch_size is _config.serial_batch_sizes


def test_layer_drop_order_names_exactly_the_drop_groups():
    # _drop_order stays in the layer until prompt 09 deletes it
    assert set(_layer._drop_order) == set(_config.drop_groups)


def test_importing_the_data_starts_no_ray():
    """In a fresh process, so the answer does not depend on test order."""
    code = (
        "import importlib, ray; "
        "importlib.import_module('Datastore.SQL.Datastore'); "
        "importlib.import_module('config.datastore'); "
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
