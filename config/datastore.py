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

"""The data SI hands to its datastore layer, the ``datastorekit`` package.

Three objects, each moved verbatim from SI's own layer, which used to define them:

``factories``
    The registry of storable classes: table name -> factory instance, in registration order.
    The datastore actor registers every entry and builds one table (or more) for each.

``drop_groups``
    The groups of tables that the ``--drop`` option of ``main.py`` drops. Each group
    lists its tables child first, so that a drop leaves no dangling foreign key.

``serial_batch_sizes``
    How many serial numbers a client leases from the actor at a time, per table. A table
    with no entry leases in batches of the package's own default (500). ``temperature`` has no
    table and is ignored.

And one function, ``tables_to_drop(groups)``: the tables of the requested ``--drop`` groups,
refused when another table would be left naming their rows (prompt 09 of the
``dk-and-rpk-migration`` campaign; its README's U5).

Every ``ShardedPool`` is given ``factories=`` and ``serial_batch_sizes=``, and ``main.py``'s
``drop_tables=tables_to_drop(...)``. Since prompt 09 deleted SI's own layer, nothing imports
this module but its callers, and it imports in a fresh process on its own: the circular import
that once made it wait for the layer is gone.
"""

from typing import Iterable, List

import sqlalchemy as sqla
from datastorekit.SQL.schema import build_schema, dependent_tables
from datastorekit.store_inventory import inventory_specs

from CosmologyConcepts.FieldValues import phi_value, pi_value
from Datastore.SQL.ObjectFactories.DimensionfulQuantity import (
    sqla_dimensionful_quantity_factory,
)
from Datastore.SQL.ObjectFactories.DimensionlessQuantity import (
    sqla_dimensionless_quantity_factory,
)
from Datastore.SQL.ObjectFactories.CosmologicalParams import sqla_cosmological_params_factory
from Datastore.SQL.ObjectFactories.CompactionFunction import (
    sqla_CompactionFunctionFactory,
    sqla_CompactionFunctionSamplesFactory,
)
from Datastore.SQL.ObjectFactories.FullInstanton import (
    sqla_FullInstantonFactory,
    sqla_FullInstantonValue_factory,
)
from Datastore.SQL.ObjectFactories.GradientCoupledInstanton import (
    sqla_GradientCoupledInstantonFactory,
    sqla_GradientCoupledInstantonValue_factory,
    sqla_GradientCoupledInstantonProfileFactory,
)
from Datastore.SQL.ObjectFactories.InflatonTrajectory import (
    sqla_InflatonTrajectory_factory,
    sqla_InflatonTrajectoryValue_factory,
)
from Datastore.SQL.ObjectFactories.SlowRollInstanton import (
    sqla_SlowRollInstantonFactory,
    sqla_SlowRollInstantonValue_factory,
)
from Datastore.SQL.ObjectFactories.QuadraticPotential import (
    sqla_QuadraticPotential_factory,
)
from Datastore.SQL.ObjectFactories.MasslessDecoupledDiffusion import (
    sqla_MasslessDecoupledDiffusion_factory,
)
from Datastore.SQL.ObjectFactories.QuarticPotential import (
    sqla_QuarticPotential_factory,
)
from Datastore.SQL.ObjectFactories.delta_Nstar import sqla_delta_Nstar_factory
from Datastore.SQL.ObjectFactories.N_init import sqla_N_init_factory
from Datastore.SQL.ObjectFactories.N_final import sqla_N_final_factory
from Datastore.SQL.ObjectFactories.n_collocation_points import (
    sqla_n_collocation_points_factory,
)
from Datastore.SQL.ObjectFactories.alpha_regularization import (
    sqla_alpha_regularization_factory,
)
from Datastore.SQL.ObjectFactories.efold import sqla_efold_factory
from Datastore.SQL.ObjectFactories.integration_metadata import (
    sqla_IntegrationSolver_factory,
)
from Datastore.SQL.ObjectFactories.redshift import sqla_redshift_factory
from Datastore.SQL.ObjectFactories.store_tag import sqla_store_tag_factory
from Datastore.SQL.ObjectFactories.tolerance import sqla_tolerance_factory
from Datastore.SQL.ObjectFactories.version import sqla_version_factory
from InflationConcepts.inflaton_mass import inflaton_mass
from InflationConcepts.quartic_coupling import quartic_coupling


factories = {
    "version": sqla_version_factory(),
    "store_tag": sqla_store_tag_factory(),
    "redshift": sqla_redshift_factory(),
    "tolerance": sqla_tolerance_factory(),
    "efold_value": sqla_efold_factory(),
    "delta_Nstar": sqla_delta_Nstar_factory(),
    "N_init": sqla_N_init_factory(),
    "N_final": sqla_N_final_factory(),
    "n_collocation_points": sqla_n_collocation_points_factory(),
    "alpha_regularization": sqla_alpha_regularization_factory(),
    "inflaton_mass": sqla_dimensionful_quantity_factory(inflaton_mass),
    "quartic_coupling": sqla_dimensionless_quantity_factory(quartic_coupling),
    "phi_value": sqla_dimensionful_quantity_factory(phi_value),
    "pi_value": sqla_dimensionful_quantity_factory(pi_value),
    "QuadraticPotential": sqla_QuadraticPotential_factory(),
    "QuarticPotential": sqla_QuarticPotential_factory(),
    "MasslessDecoupledDiffusion": sqla_MasslessDecoupledDiffusion_factory(),
    "IntegrationSolver": sqla_IntegrationSolver_factory(),
    "InflatonTrajectory": sqla_InflatonTrajectory_factory(),
    "InflatonTrajectoryValue": sqla_InflatonTrajectoryValue_factory(),
    "CosmologicalParams": sqla_cosmological_params_factory(),
    "FullInstanton": sqla_FullInstantonFactory(),
    "FullInstantonValue": sqla_FullInstantonValue_factory(),
    "GradientCoupledInstanton": sqla_GradientCoupledInstantonFactory(),
    "GradientCoupledInstantonValue": sqla_GradientCoupledInstantonValue_factory(),
    "GradientCoupledInstantonProfile": sqla_GradientCoupledInstantonProfileFactory(),
    "SlowRollInstanton": sqla_SlowRollInstantonFactory(),
    "SlowRollInstantonValue": sqla_SlowRollInstantonValue_factory(),
    "CompactionFunction": sqla_CompactionFunctionFactory(),
    "CompactionFunctionSamples": sqla_CompactionFunctionSamplesFactory(),
}


drop_groups = {
    "inflaton-trajectory":   ["InflatonTrajectoryValue", "InflatonTrajectory"],
    "full-instanton":        ["FullInstantonValue", "FullInstanton"],
    "slow-roll-instanton":   ["SlowRollInstantonValue", "SlowRollInstanton"],
    "compaction-function":   ["CompactionFunctionSamples", "CompactionFunction"],
    "gradient-coupled-instanton": [
        "GradientCoupledInstantonValue",
        "GradientCoupledInstantonProfile",
        "GradientCoupledInstanton",
    ],
}


serial_batch_sizes = {
    "store_tag": 5,
    "redshift": 200,
    "tolerance": 5,
    "temperature": 200,
    "phi_value": 200,
    "pi_value": 200,
    "efold_value": 500,
    "delta_Nstar": 10,
    "N_init": 10,
    "N_final": 10,
    "n_collocation_points": 5,
    "alpha_regularization": 5,
    "inflaton_mass": 10,
    "quartic_coupling": 10,
    "QuadraticPotential": 10,
    "QuarticPotential": 10,
    "InflatonTrajectory": 20,
    "MasslessDecoupledDiffusion": 5,
    "FullInstanton": 20,
    "FullInstantonValue": 500,
    "GradientCoupledInstanton": 20,
    "GradientCoupledInstantonValue": 500,
    "GradientCoupledInstantonProfile": 500,
    "SlowRollInstanton": 20,
    "SlowRollInstantonValue": 500,
    "CosmologicalParams": 5,
    "CompactionFunction": 20,
    "CompactionFunctionSamples": 500,
    "IntegrationSolver": 6,
}


def _naming(tables: List[str], among: List[str]) -> List[str]:
    """
    Which of ``among`` name a table of ``tables`` directly, by the rule ``dependent_tables``
    follows transitively (a foreign key, or a parent a factory's ``inventory_spec`` declares), in
    registry order. Used only to word ``tables_to_drop``'s refusal: which tables must go is
    ``dependent_tables``' answer alone.
    """
    built = build_schema(sqla.MetaData(), factories).tables
    named = {
        name: {fk.column.table.name for fk in table.foreign_keys} for name, table in built.items()
    }
    for name, spec in inventory_specs(factories).items():
        named.setdefault(name, set()).update(spec.dependencies())
    return [
        name for name in built if name in among and not named.get(name, set()).isdisjoint(tables)
    ]


def _joined(items: List[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def tables_to_drop(groups: Iterable[str]) -> List[str]:
    """
    The tables of the ``--drop`` groups named by ``groups``, each once, in ``drop_groups``' order,
    for ``ShardedPool(drop_tables=...)``.

    A name that is not a drop group raises ``ValueError``, naming it. A request that would leave
    a table naming rows it drops raises ``ValueError``: which tables must go with it is
    ``datastorekit.SQL.schema.dependent_tables``' answer, read from the registry, and the message
    names the requested groups, the tables that name their rows directly, every table that must be
    dropped with them, and the ``--drop`` groups to add (a table that must go but is in no group is
    named as a table). ``main.py`` calls this before Ray starts and refuses with exit status 2
    (dk-and-rpk-migration prompt 09; its README's U5). The package refuses the same drop itself, at
    open (``ShardedPool._refuse_drop_that_leaves_references``); this check is the earlier one, and
    speaks in groups.
    """
    requested = list(dict.fromkeys(groups))
    unknown = [group for group in requested if group not in drop_groups]
    if len(unknown) > 0:
        raise ValueError(
            f"unknown drop group(s) {unknown}: the drop groups are {list(drop_groups)}"
        )

    tables = [
        table
        for group, group_tables in drop_groups.items()
        if group in requested
        for table in group_tables
    ]
    dependents = [table for table in dependent_tables(tables, factories) if table not in tables]
    if len(dependents) == 0:
        return tables

    group_of = {
        table: group for group, group_tables in drop_groups.items() for table in group_tables
    }
    asked = [group for group in drop_groups if group in requested]
    to_add = [
        group
        for group in drop_groups
        if group not in requested and any(group_of.get(table) == group for table in dependents)
    ]
    loose = [table for table in dependents if table not in group_of]
    referrers = _naming(tables, dependents)

    additions = []
    if len(to_add) > 0:
        additions.append(f"--drop {' '.join(to_add)}")
    if len(loose) > 0:
        additions.append(
            f"the table{'s' if len(loose) > 1 else ''} {_joined(loose)}, which no drop group holds"
        )
    raise ValueError(
        f"cannot drop {_joined(asked)} alone: {_joined(referrers)} "
        f"name{'s' if len(referrers) == 1 else ''} {'its' if len(asked) == 1 else 'their'} rows, "
        f"so {_joined(dependents)} must be dropped too; add {' and '.join(additions)}"
    )
