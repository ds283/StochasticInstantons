# config/sharding.py
# Placeholder — will be populated in Prompt 3 once new concept types exist.
# The names below must remain importable by main.py and ShardedPool.

# ShardKeyType will be replaced with delta_Nstar in Prompt 3.
# For now, use a plain float as a stand-in.
ShardKeyType = float


def get_shard_key_store_id(obj) -> int:
    """Return the store_id of the shard key object. Placeholder."""
    raise NotImplementedError(
        "get_shard_key_store_id is not yet implemented. "
        "This will be defined in Prompt 3 when delta_Nstar is introduced."
    )


# Tables replicated across all shards (no shard-key dependency).
# Will be populated in Prompt 3.
replicated_tables = [
    "version",
    "store_tag",
    "tolerance",
    "redshift",
    "ExponentialPotential",
    "IntegrationSolver",
]

# Tables sharded by ShardKeyType.
# Will be populated in Prompt 3.
sharded_tables = {}

# Configuration for pool.read_table() calls used by plotting scripts.
# Will be populated in Prompt 7.
read_table_config = {}

# Configuration for pool.inventory() calls used by main.py --inventory.
# Will be populated in Prompt 7.
inventory_config = {}
