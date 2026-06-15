# main.py
import sys

import ray

from Datastore.SQL.ShardedPool import ShardedPool
from config.argument_parser import create_argument_parser
from config.sharding import (
    replicated_tables,
    sharded_tables,
    get_shard_key_store_id,
    ShardKeyType,
    read_table_config,
    inventory_config,
)

VERSION_LABEL = "2026.2.0"

parser = create_argument_parser()
args = parser.parse_args()

if args.database is None:
    parser.print_help()
    sys.exit()

ray.init(address=args.ray_address)

with ShardedPool(
    version_label=VERSION_LABEL,
    db_name=args.database,
    ShardKeyType=ShardKeyType,
    ShardKeyStoreIdGetter=get_shard_key_store_id,
    replicated_tables=replicated_tables,
    sharded_tables=sharded_tables,
    timeout=args.db_timeout,
    shards=args.shards,
    profile_agent=None,
    job_name=getattr(args, "job_name", None),
    prune_unvalidated=getattr(args, "prune_unvalidated", False),
    drop_actions=[],
    read_table_config=read_table_config,
    inventory_config=inventory_config,
) as pool:
    print(
        "StochasticInflaton pipeline is not yet implemented. "
        "This skeleton will be populated in Prompt 7."
    )
