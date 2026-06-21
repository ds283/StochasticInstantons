"""
Shared pytest fixtures for the StochasticInstanton test suite.

The ``live_pool`` session fixture provides a real ShardedPool backed by a
temporary single-shard SQLite database.  It is intended for reuse across
integration tests that need to verify store/build round-trips against an
actual datastore — not just a mock.  Upcoming prompts (scalars-only storage
mode, ``_do_not_populate`` build-time guard for FullInstanton,
SlowRollInstanton, CompactionFunction) should depend on this fixture rather
than each rolling their own.

Design constraints:
- Session-scoped: only one ShardedPool (and therefore one set of named Ray
  actors) is created per pytest invocation.  Ray's named-actor registry does
  not allow two pools with the same actor names in the same process.
- ``shards=1``: a single shard is sufficient for all current integration tests
  and keeps setup/teardown fast.
- Uses the production ``config.sharding`` objects so that the real factory
  and table wiring is exercised, not a test-only stand-in.
"""

import ray
import pytest

from Datastore.SQL.ShardedPool import ShardedPool
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    replicated_tables,
    sharded_tables,
    read_table_config,
    inventory_config,
)


@pytest.fixture(scope="session")
def live_pool(tmp_path_factory):
    """
    Session-scoped live ShardedPool backed by a temporary single-shard SQLite
    database.

    Intended for reuse by any integration test that needs a real datastore:
    deduplication checks, store/build round-trips, ``_do_not_populate`` guard
    tests, etc.  Uses the production ``config.sharding`` configuration so the
    actual factory and table wiring is exercised.

    The pool is created once per pytest session, yielded to all tests that
    request it, then torn down (ShardedPool.__exit__ + ray.shutdown) after the
    last test in the session completes.  Temporary database files are cleaned
    up automatically by pytest's ``tmp_path_factory``.
    """
    ray.init(ignore_reinit_error=True)

    db_dir = tmp_path_factory.mktemp("sharded_pool")
    db_path = db_dir / "test.sqlite"

    with ShardedPool(
        version_label="test-run",
        db_name=str(db_path),
        ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id,
        replicated_tables=replicated_tables,
        sharded_tables=sharded_tables,
        shards=1,
        profile_agent=None,
        job_name="pytest-integration",
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        yield pool

    ray.shutdown()
