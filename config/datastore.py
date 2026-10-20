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

"""The data SI hands to its datastore layer.

Three objects, each moved verbatim from the layer that used to define them:

``factories``
    The registry of storable classes: table name -> factory instance, in registration order.
    The datastore actor registers every entry and builds one table (or more) for each.

``drop_groups``
    The groups of tables that the ``--drop`` option of ``main.py`` drops. Each group
    lists its tables child first, so that a drop leaves no dangling foreign key.

``serial_batch_sizes``
    How many serial numbers a client leases from the actor at a time, per table. A table
    with no entry leases in batches of the layer's own default.

``Datastore.SQL.Datastore`` and ``Datastore.SQL.ClientPool`` read these (and, from prompt 09
of the ``dk-and-rpk-migration`` campaign, the DatastoreKit package will be given them as arguments).

Import order. Until prompt 09 deletes that layer, this module must be imported AFTER
``Datastore.SQL.Datastore`` (or ``Datastore.SQL.ClientPool``, ``Datastore.SQL.ShardedPool``, or any
``Datastore.SQL.ObjectFactories`` module). Importing the bare package ``Datastore`` or ``plotting.fetch``
does not load the layer, so it does not serve. ``Datastore/SQL/__init__.py`` imports the layer, the layer
imports this module, and this module imports the factories, which sit inside that package; a
fresh ``import config.datastore`` therefore re-enters itself and fails with a circular-import
``ImportError``. Every driver, actor and test imports the layer first, so none meets it.
"""

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
