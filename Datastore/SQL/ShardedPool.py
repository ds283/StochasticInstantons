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

import random
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import ray
import sqlalchemy as sqla

from config.defaults import DEFAULT_STRING_LENGTH
from config.sharding import ShardKeyType
from Datastore.SQL import Datastore
from Datastore.SQL.Datastore import InventoryConfigType, PathType, ReadTableConfigType
from Datastore.SQL.ProfileAgent import ProfileAgent
from Datastore.SQL.SerialPoolBroker import SerialPoolBroker
from MetadataConcepts import version


class ShardedPool:
    """
    ShardedPool manages a pool of datastore actors that cooperate to
    form a sharded SQL database
    """

    def __init__(
        self,
        version_label: str,
        db_name: PathType,
        ShardKeyType,
        ShardKeyStoreIdGetter: Callable,
        replicated_tables: List[str],
        sharded_tables: Dict[str, str],
        timeout: int = None,
        shards: int = 10,
        profile_agent: Optional[ProfileAgent] = None,
        job_name: Optional[str] = None,
        prune_unvalidated: Optional[bool] = False,
        drop_actions: Optional[List[str]] = None,
        read_table_config: Optional[ReadTableConfigType] = None,
        inventory_config: Optional[InventoryConfigType] = None,
    ) -> None:
        """
        Initialize a pool of datastore actors
        :param replicated_tables:
        :param sharded_tables:
        :param ShardKeyStoreIdGetter:
        :param version_label:
        """
        self._job_name: Optional[str] = job_name
        self._version_label: str = version_label

        self._prune_unvalidated: Optional[List[str]] = prune_unvalidated

        ## SHARDING CONFIGURATION

        # expected type of shard key
        self._ShardKeyType = ShardKeyType
        self._ShardKeyType_name: str = ShardKeyType.__name__

        # provided getter function to extract store id from a shard key object (or a proxy)
        self._ShardKeyStoreIdGetter = ShardKeyStoreIdGetter

        self._replicated_tables: List[str] = replicated_tables
        self._sharded_tables: Dict[str, str] = sharded_tables

        ## DATABASE CONFIGURATION

        self._db_name: PathType = db_name
        self._timeout: int = timeout
        self._shards: int = max(shards, 1)

        # resolve concerts the supplied db_name to an absolute path, resolving symlinks if necessary
        # this database file will be taken to be the primary database
        self._primary_file: PathType = Path(db_name).resolve()

        # shard_db_files is a map from shard number -> path representing the database on disk
        self._shard_db_files: Dict[int, PathType] = {}

        # shard_keys is a map from key id -> shard id
        self._shard_keys: Dict[int, int] = {}

        self._broker = SerialPoolBroker.options(name="SerialPoolBroker").remote(
            name="SerialPoolBroker"
        )

        self._profile_agent = profile_agent

        # if primary file is absent, all shard databases should be likewise absent
        if self._primary_file.is_dir():
            raise RuntimeError(
                f'Specified database file "{str(self._db_file)}" is a directory'
            )
        if not self._primary_file.exists():
            # ensure parent directories also exist
            self._primary_file.parents[0].mkdir(exist_ok=True, parents=True)

            stem = self._primary_file.stem
            for i in range(self._shards):
                shard_stem = f"{stem}-shard{i:04d}"
                shard_file = self._primary_file.with_stem(shard_stem)

                if shard_file.exists():
                    raise RuntimeError(
                        f'Primary database is missing, but shard "{str(shard_file)}" already exists'
                    )

                self._shard_db_files[i] = shard_file

            self._create_engine()
            self._write_shard_data()

            print(
                f'>> Created sharded datastore "{str(self._primary_file)}" with {self._shards} shards'
            )

        # otherwise, if primary exists, try to read in shard configuration from it.
        # Then, all shard databases must be present
        else:
            self._create_engine()
            self._read_shard_data()

            num_shards = len(self._shard_db_files)
            print(
                f'>> Opened existing sharded datastore "{str(self._primary_file)}" with {num_shards} shards'
            )

            if num_shards == 0:
                raise RuntimeError(
                    "No shard records were read from the sharded datastore"
                )
            if num_shards != self._shards:
                print(
                    f"!! WARNING: number of shards read from database (={num_shards}) does not match specified number of shards (={self._shards})"
                )

        # create actor pool of datastores, one for each shard
        # we read the version serial number from the first shard that we create
        shard_ids = list(self._shard_db_files.keys())

        shard0_key = shard_ids.pop()
        shard0_file = self._shard_db_files[shard0_key]

        # create the first shard datastore
        shard0_store = Datastore.options(name=f"shard{shard0_key:04d}-store").remote(
            version_label=version_label,
            db_name=shard0_file,
            timeout=self._timeout,
            my_name=f"shard{shard0_key:04d}-store",
            serial_broker=self._broker,
            profile_agent=self._profile_agent,
            prune_unvalidated=self._prune_unvalidated,
            drop_actions=drop_actions,
            read_table_config=read_table_config,
        )
        self._shards = {shard0_key: shard0_store}

        # get the version label from this store
        self._version = ray.get(
            shard0_store.object_get.remote(version, label=version_label)
        )

        # populate the remaining pool of shard stores
        self._shards.update(
            {
                key: Datastore.options(name=f"shard{key:04d}-store").remote(
                    version_label=version_label,
                    version_serial=self._version.store_id,
                    db_name=self._shard_db_files[key],
                    timeout=self._timeout,
                    my_name=f"shard{key:04d}-store",
                    serial_broker=self._broker,
                    profile_agent=self._profile_agent,
                    prune_unvalidated=self._prune_unvalidated,
                    drop_actions=drop_actions,
                    read_table_config=read_table_config,
                )
                for key in shard_ids
            }
        )

        # query a list of largest serial numbers from each shard, and notify these to the broker actor
        max_serial_data = ray.get(
            [shard.read_largest_store_ids.remote() for shard in self._shards.values()]
        )
        ray.get(
            [
                self._broker.notify_largest_store_ids.remote(payload)
                for payload in max_serial_data
            ]
        )

        self._read_table_config: Optional[ReadTableConfigType] = read_table_config
        for class_name, config in read_table_config.items():
            if class_name not in self._replicated_tables:
                raise RuntimeError(
                    f'It is only possible to configure a read-table method for a replicated table (class name="{class_name}")'
                )

        self._inventory_config: Optional[InventoryConfigType] = inventory_config

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ray.get(
            [
                shard.__exit__.remote(exc_type=None, exc_val=None, exc_tb=None)
                for shard in self._shards.values()
            ]
        )

        if self._profile_agent is not None:
            ray.get(self._profile_agent.clean_up.remote())

        if self._engine is not None:
            self._engine.dispose()

    def _create_engine(self):
        connect_args = {}
        if self._timeout is not None:
            connect_args["timeout"] = self._timeout

        self._engine = sqla.create_engine(
            f"sqlite:///{self._db_name}",
            future=True,
            connect_args=connect_args,
        )
        self._metadata = sqla.MetaData()

        self._shard_file_table = sqla.Table(
            "shards",
            self._metadata,
            sqla.Column("serial", sqla.Integer, primary_key=True, nullable=False),
            sqla.Column("filename", sqla.String(DEFAULT_STRING_LENGTH), nullable=False),
        )
        self._shard_key_config_table = sqla.Table(
            "shard_key_config",
            self._metadata,
            sqla.Column(
                "key_type",
                sqla.String(DEFAULT_STRING_LENGTH),
                primary_key=True,
                nullable=False,
            ),
        )
        self._shard_key_table = sqla.Table(
            "shard_keys",
            self._metadata,
            sqla.Column("key_serial", sqla.Integer, primary_key=True, nullable=False),
            sqla.Column(
                "shard_id",
                sqla.Integer,
                sqla.ForeignKey("shards.serial"),
                index=True,
                nullable=False,
            ),
        )
        self._replicated_tables_table = sqla.Table(
            "replicated_tables",
            self._metadata,
            sqla.Column("serial", sqla.Integer, primary_key=True, nullable=False),
            sqla.Column("table", sqla.String(DEFAULT_STRING_LENGTH), nullable=False),
        )
        self._sharded_tables_table = sqla.Table(
            "sharded_tables",
            self._metadata,
            sqla.Column("serial", sqla.Integer, primary_key=True, nullable=False),
            sqla.Column("table", sqla.String(DEFAULT_STRING_LENGTH), nullable=False),
            sqla.Column("key_attr", sqla.String(DEFAULT_STRING_LENGTH), nullable=False),
        )

    def _write_shard_data(self):
        self._shard_file_table.create(self._engine)
        self._shard_key_config_table.create(self._engine)
        self._shard_key_table.create(self._engine)
        self._replicated_tables_table.create(self._engine)
        self._sharded_tables_table.create(self._engine)

        with self._engine.begin() as conn:
            # write table of database shard files
            shard_file_values = [
                {"serial": key, "filename": str(db_name)}
                for key, db_name in self._shard_db_files.items()
            ]
            conn.execute(sqla.insert(self._shard_file_table), shard_file_values)

            # write shard key configuration type
            conn.execute(
                sqla.insert(self._shard_key_config_table),
                {"key_type": self._ShardKeyType_name},
            )

            # write table of replicated tables
            replicated_table_values = [
                {"serial": n, "table": t} for n, t in enumerate(self._replicated_tables)
            ]
            conn.execute(
                sqla.insert(self._replicated_tables_table), replicated_table_values
            )

            # write table of sharded tables
            sharded_table_values = [
                {"serial": n, "table": t, "key_attr": k}
                for n, (t, k) in enumerate(self._sharded_tables.items())
            ]
            # SQLAlchemy 2.x executes DEFAULT VALUES when given an empty list;
            # guard to avoid that when no sharded tables are configured.
            if sharded_table_values:
                conn.execute(self._sharded_tables_table.insert(), sharded_table_values)

            conn.commit()

    def _read_shard_data(self):
        with self._engine.begin() as conn:
            # read table of database shard files
            shard_files = conn.execute(
                sqla.select(
                    self._shard_file_table.c.serial,
                    self._shard_file_table.c.filename,
                )
            )
            for row in shard_files:
                serial = row.serial
                filename = Path(row.filename)

                if serial in self._shard_db_files:
                    raise RuntimeError(
                        f'Shard #{serial} already exists (database file="{str(filename)}", existing file="{str(self._shard_db_files[serial])}")'
                    )

                self._shard_db_files[row.serial] = Path(row.filename)

            # read shard key configuration type
            shard_key_configs = conn.execute(
                sqla.select(
                    self._shard_key_config_table.c.key_type,
                )
            )
            num_config = 0
            for row in shard_key_configs:
                num_config += 1
                if num_config == 1:
                    if row.key_type != self._ShardKeyType_name:
                        raise RuntimeError(
                            f'Existing ShardedPool was configured with shard key type "{row.key_attr}", but provided type was "{self._ShardKeyType_name}"'
                        )

                elif num_config > 1:
                    raise print(
                        f'ShardedPool has unexpected multiple shard key types: {num_config}="{row.key_attr}"'
                    )
            if num_config == 0:
                raise RuntimeError(f"No configured shard key type was found")
            elif num_config > 1:
                raise RuntimeError(f"Multiple configured shard key types were found")

            # read table of replicated tables
            replicated_table_data = conn.execute(
                sqla.select(
                    self._replicated_tables_table.c.serial,
                    self._replicated_tables_table.c.table,
                )
            )
            missing_read_replicated = set()
            missing_supplied_replicated = set(self._replicated_tables)
            for row in replicated_table_data:
                if row.table not in missing_supplied_replicated:
                    missing_read_replicated.add(row.table)
                missing_supplied_replicated.discard(row.table)
            if len(missing_read_replicated) > 0:
                print(
                    f"The following replicated tables are configured in the existing ShardedPool, but were not supplied to the constructor:"
                )
                for table in missing_read_replicated:
                    print(f"  {table}")
            if len(missing_supplied_replicated) > 0:
                print(
                    f"The following replicated tables were supplied to the constructor, but are not configured in the existing ShardedPool:"
                )
                for table in missing_supplied_replicated:
                    print(f"  {table}")
            if len(missing_read_replicated) > 0 or len(missing_supplied_replicated) > 0:
                raise RuntimeError(
                    f"Mismatch between replicated tables supplied to the constructor and read from the existing ShardedPool"
                )

            # read table of sharded tables
            sharded_table_data = conn.execute(
                sqla.select(
                    self._sharded_tables_table.c.serial,
                    self._sharded_tables_table.c.table,
                    self._sharded_tables_table.c.key_attr,
                )
            )
            missing_read_sharded = set()
            mismatching_key_attr = {}
            missing_supplied_sharded = set(self._sharded_tables.keys())
            for row in sharded_table_data:
                if row.table not in missing_supplied_sharded:
                    missing_read_sharded.add(row.table)
                attr = self._sharded_tables[row.table]
                if row.key_attr != attr:
                    mismatching_key_attr[row.table] = {
                        "supplied": attr,
                        "configured": row.key_attr,
                    }
                missing_supplied_sharded.discard(row.table)
            if len(missing_read_sharded) > 0:
                print(
                    f"The following sharded tables are configured in the existing ShardedPool, but were not supplied to the constructor:"
                )
                for table in missing_read_sharded:
                    print(f"  {table}")
            if len(missing_supplied_sharded) > 0:
                print(
                    f"The following sharded tables are supplied to the constructor, but are not configured in the existing ShardedPool:"
                )
                for table in missing_supplied_sharded:
                    print(f"  {table}")
            if len(mismatching_key_attr) > 0:
                print(
                    f"The following sharded tables were configured with a different key attribute in the existing ShardedPool:"
                )
                for table, data in mismatching_key_attr.items():
                    print(
                        f'  {table}: configured key="{data["configured"]}", supplied key="{data["supplied"]}"'
                    )
            if len(missing_read_sharded) > 0 or len(missing_supplied_sharded) > 0:
                raise RuntimeError(
                    f"Mismatch between sharded tables supplied to the constructor and read from the existing ShardedPool"
                )
            if len(mismatching_key_attr) > 0:
                raise RuntimeError(
                    f"Some sharded tables had mismatching key configurations in the existing ShardedPool"
                )

            # read table of existing shard keys
            keys = conn.execute(
                sqla.select(
                    self._shard_key_table.c.key_serial,
                    self._shard_key_table.c.shard_id,
                )
            )
            for key in keys:
                self._shard_keys[key.key_serial] = key.shard_id

    def object_get(self, ObjectClass, **kwargs):
        if isinstance(ObjectClass, str):
            cls_name = ObjectClass
        else:
            cls_name = ObjectClass.__name__

        if cls_name in self._replicated_tables:
            return self._get_impl_replicated_table(cls_name, kwargs)

        if cls_name in self._sharded_tables.keys():
            return self._get_impl_sharded_table(cls_name, kwargs)

        raise RuntimeError(
            f'Unable to dispatch object_get() for item of type "{cls_name}"'
        )

    def _get_impl_replicated_table(self, cls_name, kwargs):
        # pick a shard id at random to be the "controlling" shard.
        # we will push an initial 'get' to this controlling shard.
        # if a new database object was created by the get, we then have to push a replica
        # to all the other shards
        shard_ids = list(self._shards.keys())
        i = random.randrange(len(shard_ids))

        # swap this entry with the last element, then pop it
        shard_ids[i], shard_ids[-1] = shard_ids[-1], shard_ids[i]
        shard_key = shard_ids.pop()

        # for replicated tables, we should query/insert into *one* datastore, and then enforce
        # that all other datastores get the same store_id; here, there is no need to use our internal
        # information about the next-allocated store_id, and in fact doing so would make the logic
        # here much more complicated. So we avoid that.
        ref = self._shards[shard_key].object_get.remote(cls_name, **kwargs)
        objects = ray.get(ref)

        # was this a vectorized get?
        if "payload_data" in kwargs:
            payload_data = kwargs["payload_data"]

            if len(payload_data) != len(objects):
                raise RuntimeError(
                    f"object_get() data returned from selected datastore (shared={shard_key}) has a different length (length={len(objects)}) to payload data (length={len(payload_data)})"
                )

            # add explicit serial specifier
            new_payload = []
            for i in range(len(payload_data)):
                # if this object has a valid store_id and has the _new_insert or _updated metadata
                # flags set, push to all the remaining shards in order to keep them in sync
                if (
                    hasattr(objects[i], "_my_id")
                    and objects[i]._my_id is not None
                    and (
                        hasattr(objects[i], "_new_insert")
                        or hasattr(objects[i], "_updated")
                    )
                ):
                    payload_data[i]["serial"] = objects[i].store_id
                    new_payload.append(payload_data[i])

            # queue work items to replicate each object in all other shards (recall that shard_key has already been popped from shard_ids,
            # so there is no double insertion here)
            ray.get(
                [
                    self._shards[key].object_get.remote(
                        cls_name, payload_data=new_payload
                    )
                    for key in shard_ids
                ]
            )
        else:
            # this was a scalar get

            # if this object has a valid store_id and has the _new_insert or _updated
            # metadata flags set, push to all remaining shards in order to keep them in sync
            if (
                hasattr(objects, "_my_id")
                and objects._my_id is not None
                and (hasattr(objects, "_new_insert") or hasattr(objects, "_updated"))
            ):
                ray.get(
                    [
                        self._shards[key].object_get.remote(
                            cls_name, serial=objects.store_id, **kwargs
                        )
                        for key in shard_ids
                    ]
                )

        # test whether this query was for a shard key, and, if so, assign any shard keys
        # that are missing
        if cls_name == self._ShardKeyType_name:
            self._assign_shard_keys(objects)

        # return original object (we just discard any copies returned from other shards)
        return ref

    def _get_impl_sharded_table(self, cls_name, kwargs):
        # for sharded tables, we should query/insert into only the appropriate shard
        shard_key_field = self._sharded_tables[cls_name]

        # is this a vectorized get?
        if "payload_data" in kwargs:
            payload_data = kwargs["payload_data"]

            work_refs = []
            for item in payload_data:
                key = item[shard_key_field]
                shard_id = self._shard_keys[self._ShardKeyStoreIdGetter(key)]

                work_refs.append(
                    self._shards[shard_id].object_get.remote(cls_name, **item)
                )

            return work_refs
            # TODO: consider consolidating all objects for the same shard into a list, for efficiency

        # otherwise, can assume this is a scalar get
        key = kwargs[shard_key_field]
        shard_id = self._shard_keys[self._ShardKeyStoreIdGetter(key)]

        return self._shards[shard_id].object_get.remote(cls_name, **kwargs)

    def object_get_vectorized(self, ObjectClass, shard_key, payload_data):
        if isinstance(ObjectClass, str):
            cls_name = ObjectClass
        else:
            cls_name = ObjectClass.__name__

        if cls_name not in self._sharded_tables:
            raise RuntimeError(
                f"ShardedPool: it is only possible to vectorize object_get() over a sharded table (object type={cls_name})"
            )

        if isinstance(shard_key, ShardKeyType):
            _real_shard_key = shard_key

        else:
            shard_key_field = self._sharded_tables[cls_name]
            if shard_key_field not in shard_key:
                raise RuntimeError(
                    f'ShardedPool: expected shard key "{shard_key_field}" to be provided for object type "{cls_name}", but instead received keys: {shard_key.keys()}'
                )

            _real_shard_key = shard_key[shard_key_field]

        shard_id = self._shard_keys[self._ShardKeyStoreIdGetter(_real_shard_key)]

        return self._shards[shard_id].object_get.remote(
            cls_name, payload_data=payload_data
        )

    def object_read_batch(self, ObjectClass, shard_key, **payload):
        if isinstance(ObjectClass, str):
            cls_name = ObjectClass
        else:
            cls_name = ObjectClass.__name__

        if cls_name not in self._sharded_tables:
            raise RuntimeError(
                f"ShardedPool: it is only possible to apply object_read_batch() to a sharded table (object type={cls_name})"
            )

        shard_key_field = self._sharded_tables[cls_name]
        if not hasattr(shard_key, shard_key_field):
            raise RuntimeError(
                f'ShardedPool: expected shard key "{shard_key_field}" to be provided for object type "{cls_name}", but instead received keys: {shard_key.__attrs__}'
            )

        shard_id = self._shard_keys[
            self._ShardKeyStoreIdGetter(shard_key[shard_key_field])
        ]

        payload.update(shard_key)
        return self._shards[shard_id].object_read_batch.remote(cls_name, **payload)

    def object_store(self, objects):
        if isinstance(objects, list) or isinstance(objects, tuple):
            payload_data = objects
            scalar = False
        else:
            payload_data = [objects]
            scalar = True

        work_refs = []
        for item in payload_data:
            cls_name = type(item).__name__

            if cls_name in self._replicated_tables:
                work_refs.extend(self._store_impl_replicated_table(cls_name, item))
                continue

            if cls_name in self._sharded_tables.keys():
                work_refs.extend(self._store_impl_sharded_table(cls_name, item))
                continue

            raise RuntimeError(
                f'Unable to dispatch object_get() for item of type "{cls_name}"'
            )

        if scalar:
            return work_refs[0]

        return work_refs

    def _store_impl_replicated_table(self, cls_name, item):
        # pick a shard id at random to be the "controlling" shard
        # we will push an initial 'store' to this controlling shard.
        # if a new database object was created by the get, we then have to push a replica
        # to all the other shards
        shard_ids = list(self._shards.keys())
        i = random.randrange(len(shard_ids))

        # swap this entry with the last element, then pop it
        shard_ids[i], shard_ids[-1] = shard_ids[-1], shard_ids[i]
        shard_key = shard_ids.pop()

        ref = self._shards[shard_key].object_store.remote(item)
        obj = ray.get(ref)

        # now push the object, complete with its new 'store_id', to all the other shards
        if not hasattr(obj, "_my_id") or obj._my_id is None:
            raise RuntimeError(
                f'Stored object of type "{cls_name}" was not assigned a store_id field'
            )

        ray.get([self._shards[key].object_store.remote(obj) for key in shard_ids])

        return [ref]

    def _store_impl_sharded_table(self, cls_name, item):
        # item need only be pushed to a single shard
        # unlike the replicated case,
        # we don't have to care about what happens to its store_id

        shard_key_field = self._sharded_tables[cls_name]
        if not hasattr(item, shard_key_field):
            raise RuntimeError(
                f'Unable to determine shard, because object of type "{cls_name}" has no "{shard_key_field}" attribute'
            )

        key = getattr(item, shard_key_field)
        shard_id = self._shard_keys[self._ShardKeyStoreIdGetter(key)]

        # TODO: consider consolidating all stores for the same shard into a list, for efficiency
        return [self._shards[shard_id].object_store.remote(item)]

    def object_validate(self, objects):
        if isinstance(objects, list) or isinstance(objects, tuple):
            payload_data = objects
            scalar = False
        else:
            payload_data = [objects]
            scalar = True

        work_refs = []
        for item in payload_data:
            cls_name = type(item).__name__

            if cls_name in self._replicated_tables:
                work_refs.extend(self._validate_impl_replicated_table(cls_name, item))
                continue

            if cls_name in self._sharded_tables.keys():
                work_refs.extend(self._validate_impl_sharded_table(cls_name, item))
                continue

            raise RuntimeError(
                f'Unable to dispatch object_validate() for item of type "{cls_name}"'
            )

        if scalar:
            return work_refs[0]

        return work_refs

    def _validate_impl_replicated_table(self, cls_name, item):
        # pick a shard id at random to be the "controlling" shard
        # we will push an initial 'validate' to this controlling shard.
        shard_ids = list(self._shards.keys())
        i = random.randrange(len(shard_ids))

        # swap this entry with the last element, then pop it
        shard_ids[i], shard_ids[-1] = shard_ids[-1], shard_ids[i]
        shard_key = shard_ids.pop()

        ref = self._shards[shard_key].object_validate.remote(item)
        outcome = ray.get(ref)

        # if object did not validate, do not push validation requests to remaining shards
        if outcome is False or outcome is None:
            return [ref]

        outcomes = ray.get(
            [self._shards[key].object_validate.remote(item) for key in shard_ids]
        )
        if any(oc is not True for oc in outcomes):
            print(f"!! Validation outcomes did not agree between shards:")
            print(f"|    outcomes = {outcomes}")
            raise RuntimeError(
                f'Object validation produced different outcomes on different shards for replicated object of type "{cls_name}"'
            )

        return [ref]

    def _validate_impl_sharded_table(self, cls_name, item):
        # item need only be validated on a single shard
        shard_key_field = self._sharded_tables[cls_name]
        if not hasattr(item, shard_key_field):
            raise RuntimeError(
                f'Unable to determine shard, because object of type "{cls_name}" has no "{shard_key_field}" attribute'
            )

        key = getattr(item, shard_key_field)
        shard_id = self._shard_keys[self._ShardKeyStoreIdGetter(key)]

        # TODO: consider consolidating all validates for the same shard into a list, for efficiency
        return [self._shards[shard_id].object_validate.remote(item)]

    def _assign_shard_keys(self, obj):
        if isinstance(obj, list):
            data = obj
        else:
            data = [obj]

        # assign any shard keys that we can, without going out to the database
        # (because this is bound to be slower)
        seen_store_ids = set()
        missing_keys = []
        for item in data:
            if not isinstance(item, self._ShardKeyType):
                raise RuntimeError(
                    f'shard keys should be of type "{self._ShardKeyType_name}"'
                )

            if item.store_id not in self._shard_keys and item.store_id not in seen_store_ids:
                missing_keys.append(item)
                seen_store_ids.add(item.store_id)

        # if no work to do, return
        if len(missing_keys) == 0:
            return

        # otherwise, we have to populate keys
        # try to load balance by working out which shard has the fewest keys
        loads = {key: 0 for key in self._shards.keys()}
        for shard in self._shard_keys.values():
            loads[shard] = loads[shard] + 1

        with self._engine.begin() as conn:
            for item in missing_keys:
                # find which shard has the current minimum load
                if len(loads) > 0:
                    new_shard = min(loads, key=loads.get)
                else:
                    new_shard = list(self._shards.keys()).pop()

                # insert a new record for this key
                result = conn.execute(
                    sqla.insert(self._shard_key_table),
                    {"key_serial": item.store_id, "shard_id": new_shard},
                )
                assigned_serial = result.inserted_primary_key[0]

                if assigned_serial != item.store_id:
                    print(
                        f"!! _assign_shard_keys MISMATCH: "
                        f"store_id={item.store_id}, "
                        f"assigned key_serial={assigned_serial}, "
                        f"shard={new_shard}"
                    )
                # else:
                #     print(
                #         f">> _assign_shard_keys: "
                #         f"store_id={item.store_id} → key_serial={assigned_serial} → shard={new_shard}"
                #     )

                self._shard_keys[item.store_id] = new_shard
                loads[new_shard] = loads[new_shard] + 1

            conn.commit()
            # print(
            #     f">> _assign_shard_keys: committed {len(missing_keys)} new assignment(s). "
            #     f"Full mapping: { {k: v for k, v in sorted(self._shard_keys.items())} }"
            # )

    def read_table(self, cls, *args, **kwargs):
        """
        Provide a generic implementation to read a replicated table using an underlying Datastore
        :param kwargs:
        :return:
        """
        if self._read_table_config is None:
            raise RuntimeError("ShardedPool: the read_table service is not configured")

        if isinstance(cls, str):
            class_name = cls
        else:
            class_name = cls.__name__

        if class_name in self._sharded_tables:
            raise RuntimeError(
                f'ShardedPool: the read_table service is only available for replicated tables, but "{class_name}" is configured as a sharded table'
            )

        if class_name not in self._read_table_config:
            raise RuntimeError(
                f'ShardedPool: the read_table service is not available for objects of class "{class_name}"'
            )

        # we only need to read the table from a single shard, so pick one at random
        shard_ids = list(self._shards.keys())
        i = random.randrange(len(shard_ids))

        # swap this entry with the last element, then pop it
        shard_ids[i], shard_ids[-1] = shard_ids[-1], shard_ids[i]
        shard_key = shard_ids.pop()

        shard = self._shards[shard_key]

        return shard.read_table.remote(class_name, *args, **kwargs)

    def _merge_queue(self, merge_queue, class_name, config):
        data = merge_queue.pop()

        for next_data in merge_queue:
            for field, current in data.items():
                if field not in config:
                    raise RuntimeError(
                        f'ShardedPool: the inventory configuration does not specify a merge policy for field "{field}"'
                    )

                policy = config[field]
                next = next_data[field]

                if isinstance(current, list):
                    if policy == "extend":
                        current.extend(next)
                        continue

                elif isinstance(current, set):
                    if policy == "extend":
                        current.update(next)
                        continue

                elif isinstance(current, datetime):
                    if not isinstance(next, datetime) and next is not None:
                        raise RuntimeError(
                            f'ShardedPool: the inventory configuration specifies a merge policy for field "{field}" that requires a datetime, but the value "{next}" is not a datetime'
                        )

                    if policy == "earliest":
                        if next is not None and next < current:
                            data[field] = next
                        continue

                    elif policy == "latest":
                        if next is not None and next > current:
                            data[field] = next
                        continue

                elif current is None:
                    if next is not None:
                        data[field] = next
                    continue

                raise RuntimeError(
                    f'ShardedPool: unknown merge policy "{policy}" for field "{field}" of type "{type(current).__name__}" when merging inventory for object class "{class_name}"'
                )

        return data

    def inventory(self, cls, *args, **kwargs):
        """
        Return a human-readable inventory of the Datastore contents for a particular object class
        :param cls:
        :return:
        """
        if isinstance(cls, str):
            class_name = cls
        else:
            class_name = cls.__name__

        shard_ids = list(self._shards.keys())

        if class_name in self._replicated_tables:
            # we only need to read the table from a single shard, so pick one at random
            i = random.randrange(len(shard_ids))

            # swap this entry with the last element, then pop it
            shard_ids[i], shard_ids[-1] = shard_ids[-1], shard_ids[i]
            shard_key = shard_ids.pop()

            shard = self._shards[shard_key]
            return ray.get(shard.inventory.remote(class_name, *args, **kwargs))

        if class_name in self._sharded_tables:
            if self._inventory_config is None:
                raise RuntimeError(
                    f"ShardedPool: the inventory service is not configured"
                )

            if class_name not in self._inventory_config:
                raise RuntimeError(
                    f'ShardedPool: the inventory service is not available for objects of class "{class_name}"'
                )

            # read
            data_queue = ray.get(
                [
                    self._shards[key].inventory.remote(class_name, *args, **kwargs)
                    for key in shard_ids
                ]
            )

            if len(data_queue) == 0:
                raise RuntimeError(
                    f'ShardedPool: no inventory data was returned from the shards for object class "{class_name}"'
                )

            # test whether merging takes place at the top level in the returned inventory, or whether we have a set of labels at the top level
            field = list(data_queue[0].keys()).pop()
            if isinstance(data_queue[0][field], dict):
                labels = list(data_queue[0].keys())

                merged = {}
                for label in labels:
                    queue = [d[label] for d in data_queue]
                    config = self._inventory_config[class_name][label]
                    merged[label] = self._merge_queue(queue, class_name, config)

            else:
                merged = self._merge_queue(
                    data_queue, class_name, self._inventory_config[class_name]
                )

            return merged

        raise RuntimeError(
            f'Unable to dispatch inventory() for item of type "{class_name}"'
        )
