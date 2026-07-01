from InflationConcepts.delta_Nstar import delta_Nstar

# delta_Nstar (ΔN★) is the shard key: each shard holds data for one value of ΔN★.
ShardKeyType = delta_Nstar


def get_shard_key_store_id(obj) -> int:
    """Return the store_id of the delta_Nstar shard key embedded in obj."""
    return obj.shard_key.store_id


# Tables replicated identically across all shards.
# delta_Nstar must be in this list: ShardedPool._get_impl_replicated_table()
# triggers _assign_shard_keys() when it sees ShardKeyType.__name__ here.
replicated_tables = [
    "version",
    "store_tag",
    "tolerance",
    "efold_value",
    "y_value",
    "delta_Nstar",
    "N_init",
    "N_final",
    "inflaton_mass",
    "quartic_coupling",
    "phi_value",
    "pi_value",
    "QuadraticPotential",
    "QuarticPotential",
    "MasslessDecoupledDiffusion",
    "IntegrationSolver",
    "InflatonTrajectory",
    "InflatonTrajectoryValue",
    "CosmologicalParams",
]

# Tables sharded by delta_Nstar.
# delta_Nstar itself is NOT listed here: it is the shard key type, routed
# entirely via replicated_tables (above). Listing it here as well makes
# ShardedPool.read_table() reject it as "sharded" even though it is fully
# replicated, since that check only tests membership in this dict.
sharded_tables = {
    "FullInstanton": "delta_Nstar",
    "FullInstantonValue": "delta_Nstar",
    "SlowRollInstanton": "delta_Nstar",
    "SlowRollInstantonValue": "delta_Nstar",
    "CompactionFunction": "delta_Nstar",
    "CompactionFunctionSamples": "delta_Nstar",
}

# Configuration for pool.read_table() calls.
# Only replicated tables may appear here (ShardedPool enforces this).
# tables_arg=True causes Datastore to pass its full tables dict as `tables` kwarg.
read_table_config = {
    "InflatonTrajectory": {"tables_arg": True},
    "delta_Nstar": {"tables_arg": False},
    "efold_value": {"tables_arg": False},
    "y_value": {"tables_arg": False},
    "inflaton_mass": {"tables_arg": False},
    "quartic_coupling": {"tables_arg": False},
    "phi_value": {"tables_arg": False},
    "pi_value": {"tables_arg": False},
}

# Merge policies for pool.inventory() calls on sharded tables.
# Each field in the factory's inventory() return value needs a merge policy:
#   lists     → "extend"
#   datetimes → "earliest" or "latest"
_instanton_merge = {
    "validated": {
        "labels": "extend",
        "versions": "extend",
        "earliest_timestamp": "earliest",
        "latest_timestamp": "latest",
    },
    "unvalidated": {
        "labels": "extend",
        "versions": "extend",
        "earliest_timestamp": "earliest",
        "latest_timestamp": "latest",
    },
}

inventory_config = {
    "FullInstanton": _instanton_merge,
    "SlowRollInstanton": _instanton_merge,
    "CompactionFunction": _instanton_merge,
}
