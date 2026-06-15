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

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import ray
import sqlalchemy as sqla
from sqlalchemy.exc import SQLAlchemyError

from config.defaults import DEFAULT_STRING_LENGTH
from utilities import format_time

DEFAULT_NOTIFY_TIME_INTERVAL = 30 * 60

TIME_2_SECONDS = 2
TIME_5_SECONDS = 5
TIME_10_SECONDS = 10
TIME_30_SECONDS = 30

_SlowQueryRecordType = dict[str, int]


@ray.remote
class ProfileAgent:
    def __init__(
        self,
        db_name: str,
        timeout: Optional[int] = None,
        label: Optional[str] = None,
        notify_time_interval: Optional[int] = DEFAULT_NOTIFY_TIME_INTERVAL,
    ):
        self._timeout: Optional[int] = timeout
        self._notify_time_interval: Optional[int] = notify_time_interval

        self._start_time: float = time.perf_counter()
        self._last_notify_time: float = self._start_time

        self._db_file: Path = Path(db_name).resolve()

        if self._db_file.is_dir():
            raise RuntimeError(
                f'Specified profile agent database file "{str(self._db_file)}" is a directory"'
            )
        elif not self._db_file.exists():
            # create parent directories if they do not already exist
            self._db_file.parents[0].mkdir(parents=True, exist_ok=True)
            self._create_engine()
            self._ensure_tables()
        else:
            self._create_engine()
            self._ensure_tables()

        if label is not None:
            self._label = label
        else:
            self._label = (
                f"job-start-{datetime.now().replace(microsecond=0).isoformat()}"
            )

        with self._engine.begin() as conn:
            obj = conn.execute(sqla.insert(self._job_table), {"label": self._label})

            self._job_id = obj.lastrowid

        self._total_events: int = 0
        self._events_at_last_notify: int = None

        self._has_slow_queries: bool = False

        self._new_2sec_queries: _SlowQueryRecordType = {}
        self._new_5sec_queries: _SlowQueryRecordType = {}
        self._new_10sec_queries: _SlowQueryRecordType = {}
        self._new_30sec_queries: _SlowQueryRecordType = {}

        self._2sec_queries: _SlowQueryRecordType = {}
        self._5sec_queries: _SlowQueryRecordType = {}
        self._10sec_queries: _SlowQueryRecordType = {}
        self._30sec_queries: _SlowQueryRecordType = {}

    def _create_engine(self):
        connect_args = {}
        if self._timeout is not None:
            connect_args["timeout"] = self._timeout

        self._engine = sqla.create_engine(
            f"sqlite:///{str(self._db_file)}",
            future=True,
            connect_args=connect_args,
        )
        self._metadata = sqla.MetaData()
        self._inspector = sqla.inspect(self._engine)

        self._job_table = sqla.Table(
            "jobs",
            self._metadata,
            sqla.Column("serial", sqla.Integer, primary_key=True),
            sqla.Column("label", sqla.String(DEFAULT_STRING_LENGTH)),
        )
        self._profile_table = sqla.Table(
            "profile_data",
            self._metadata,
            sqla.Column("serial", sqla.Integer, primary_key=True),
            sqla.Column(
                "job_serial",
                sqla.Integer,
                sqla.ForeignKey("jobs.serial"),
                index=True,
                nullable=False,
            ),
            sqla.Column(
                "source",
                sqla.String(DEFAULT_STRING_LENGTH),
                nullable=False,
            ),
            sqla.Column("method", sqla.String(DEFAULT_STRING_LENGTH), nullable=False),
            sqla.Column("start_time", sqla.DateTime(), nullable=False),
            sqla.Column("elapsed", sqla.Float(64), nullable=False),
            sqla.Column("metadata", sqla.String(DEFAULT_STRING_LENGTH)),
        )

    def _ensure_tables(self):
        if not self._inspector.has_table("jobs"):
            self._job_table.create(self._engine)

        if not self._inspector.has_table("profile_data"):
            self._profile_table.create(self._engine)

    def write_batch(self, batch):
        try:
            with self._engine.begin() as conn:
                for item in batch:
                    self._total_events = self._total_events + 1

                    elapsed = item["elapsed"]
                    method = item["method"]
                    _ = conn.execute(
                        sqla.insert(self._profile_table),
                        {
                            "job_serial": self._job_id,
                            "source": item["source"],
                            "method": method,
                            "start_time": item["start_time"],
                            "elapsed": elapsed,
                            "metadata": item["metadata"],
                        },
                    )

                    if elapsed > TIME_2_SECONDS:
                        self._has_slow_queries = True

                        if elapsed > TIME_30_SECONDS:
                            if method in self._new_30sec_queries:
                                self._new_30sec_queries[method] = (
                                    self._new_30sec_queries[method] + 1
                                )
                            else:
                                self._new_30sec_queries[method] = 1
                        elif elapsed > TIME_10_SECONDS:
                            if method in self._new_10sec_queries:
                                self._new_10sec_queries[method] = (
                                    self._new_10sec_queries[method] + 1
                                )
                            else:
                                self._new_10sec_queries[method] = 1
                        elif elapsed > TIME_5_SECONDS:
                            if method in self._new_5sec_queries:
                                self._new_5sec_queries[method] = (
                                    self._new_5sec_queries[method] + 1
                                )
                            else:
                                self._new_5sec_queries[method] = 1
                        else:
                            if method in self._new_2sec_queries:
                                self._new_2sec_queries[method] = (
                                    self._new_2sec_queries[method] + 1
                                )
                            else:
                                self._new_2sec_queries[method] = 1

        except SQLAlchemyError as e:
            print(f"!! ProfileAgent: insert error, payload = {batch}")
            raise e

        if self._notify_time_interval is not None:
            now = time.perf_counter()
            if now - self._last_notify_time > self._notify_time_interval:
                self._notify_progress(now)
                self._last_notify_time = now
                self._events_at_last_notify = self._total_events

    def _notify_progress(self, now):
        timestamp = datetime.now()
        msg = f"[DATABASE] {timestamp:%Y-%m-%d %H:%M:%S%z}: {self._total_events} total database events"
        if self._events_at_last_notify is not None:
            msg += f" | {self._total_events - self._events_at_last_notify} since last notification ({format_time(now-self._last_notify_time)} ago)"
        print(msg)

        if self._has_slow_queries:
            new_2sec_queries = sum(self._new_2sec_queries.values())
            num_2sec_queries = sum(self._2sec_queries.values()) + new_2sec_queries
            new_5sec_queries = sum(self._new_5sec_queries.values())
            num_5sec_queries = sum(self._5sec_queries.values()) + new_5sec_queries
            new_10sec_queries = sum(self._new_10sec_queries.values())
            num_10sec_queries = sum(self._10sec_queries.values()) + new_10sec_queries
            new_30sec_queries = sum(self._new_30sec_queries.values())
            num_30sec_queries = sum(self._30sec_queries.values()) + new_30sec_queries

            msg = f"-- Slow queries reported (total): {num_2sec_queries} >2 sec ({new_2sec_queries} new), {num_5sec_queries} >5 sec ({new_5sec_queries} new), {num_10sec_queries} >10 sec ({new_10sec_queries} new), {num_30sec_queries} >30 sec ({new_30sec_queries} new)"
            print(msg)

            def print_slow_query_records(label: str, new: _SlowQueryRecordType):
                if len(new) == 0:
                    return

                data = sorted(new.items(), key=lambda q: q[1], reverse=True)
                print(f"   New {label} queries:")
                for method, count in data:
                    print(f"     ## {method}: {count}")

            def merge_slow_query_records(
                total: _SlowQueryRecordType, new: _SlowQueryRecordType
            ):
                for method, count in new.items():
                    if method in total:
                        total[method] = total[method] + count
                    else:
                        total[method] = count

                # empty "new" dict; because dicts are mutable, this will clear the corresponding
                # dictionary in the parent scope
                new.clear()

            print_slow_query_records(">2 sec", self._new_2sec_queries)
            print_slow_query_records(">5 sec", self._new_5sec_queries)
            print_slow_query_records(">10 sec", self._new_10sec_queries)
            print_slow_query_records(">30 sec", self._new_30sec_queries)

            merge_slow_query_records(self._2sec_queries, self._new_2sec_queries)
            merge_slow_query_records(self._5sec_queries, self._new_5sec_queries)
            merge_slow_query_records(self._10sec_queries, self._new_10sec_queries)
            merge_slow_query_records(self._30sec_queries, self._new_30sec_queries)

    def clean_up(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

        if self._notify_time_interval is not None:
            now = time.perf_counter()
            self._notify_progress(now)


class ProfileBatcher:
    def __init__(
        self, profile_agent, source_label: str, batch_size: Optional[int] = 100
    ):
        self._profile_agent = profile_agent
        self._source_label = source_label

        self._batch_size = batch_size
        self._batch = []

    def write(self, method: str, start_time: datetime, elapsed: float, metadata: str):
        if self._profile_agent is None:
            return

        self._batch.append(
            {
                "source": self._source_label,
                "method": method,
                "start_time": start_time,
                "elapsed": elapsed,
                "metadata": metadata,
            }
        )

        if len(self._batch) > self._batch_size:
            self._push_batch()

    def _push_batch(self):
        if len(self._batch) > 0:
            self._profile_agent.write_batch.remote(self._batch)
            self._batch = []

    def clean_up(self) -> None:
        self._push_batch()


class ProfileBatchManager:
    def __init__(
        self,
        batcher,
        method: str,
        metadata: Optional[dict] = None,
        num_items: Optional[int] = None,
    ):
        self._batcher = batcher

        self._method = method
        self._metadata = metadata if metadata is not None else {}

        if self._method is None:
            raise RuntimeError("method cannot be None")

        if not isinstance(self._metadata, dict):
            raise RuntimeError("metadata should be a dict")

        self._start_time = None
        self._perf_timer_start = None

        self._num_items = num_items

    def __enter__(self):
        self.start_time = datetime.now()
        self.perf_timer_start = time.perf_counter()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.perf_timer_start

        if self._num_items is not None and self._num_items > 0:
            self._metadata.update(
                {
                    "num_items": self._num_items,
                    "time_per_item": elapsed / self._num_items,
                }
            )

        self._batcher.write(
            method=self._method,
            start_time=self.start_time,
            elapsed=elapsed,
            metadata=str(self._metadata) if len(self._metadata) > 0 else None,
        )

    def update_metadata(self, data):
        self._metadata.update(data)

    def update_num_items(self, num_items: int):
        self._num_items = num_items
