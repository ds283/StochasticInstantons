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
    "delta_Nstar",
    "inflaton_mass",
    "quartic_coupling",
    "QuadraticPotential",
    "QuarticPotential",
    "IntegrationSolver",
]

# Tables sharded by delta_Nstar. Populated in Prompt 3+.
sharded_tables = {}

# Configuration for pool.read_table() calls. Populated in Prompt 7.
read_table_config = {}

# Configuration for pool.inventory() calls. Populated in Prompt 7.
inventory_config = {}
