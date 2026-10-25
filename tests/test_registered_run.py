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

"""What `RunDrivers/registered_run.py` records when it registers a run (rrk-adoption prompt 03,
W2, W3 and W6 test 1), and what it hands the program it runs.

Each test runs the wrapper's `main` in this process on a stand-in program
(`registered_run_helpers.standin_program`), into a temporary runs root, with `ray.init` and
`ray.shutdown` replaced by stand-ins before the wrapper wraps them (`registered_run_helpers.
in_process`). The database is a path in the temporary directory that no test here creates. One
test calls `register` alone with `program=MAIN_PY`, which reads no `main.py` text and runs nothing
(ChamPBH's note 03, ruling 4). The scope tests parse `main.py`'s arguments, which reads
`quadratic-minimal.yaml` at the root and starts nothing. No Ray is initialised, and nothing under
`var/` is read or written.
"""

import hashlib
import signal
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import runregistrykit

from RunDrivers import registered_run
from registered_run_helpers import (  # noqa: F401
    ADDRESS,
    REPO_ROOT,
    TITLE,
    WRAPPER,
    Recorder,
    StringWriter,
    TakeOver,
    in_process,
    install_ray_like_handler,
    no_ray_at_the_end,
    only_run,
    ray_like_sigterm_handler,
    read_json,
    read_record,
    standin_program,
    wrapper_argv,
)

# rrk-adoption prompt 04's reference build, as dk-and-rpk-migration's build.sh runs main.py, with
# 04's store and job name
REFERENCE = [
    "--config",
    "quadratic-minimal.yaml",
    "--database",
    "var/datastores/rrk-adoption-04-reference.sqlite",
    "--job-name",
    "rrk-adoption-04-reference",
    "--targets",
    "homogeneous",
    "--n-collocation-points",
    "5",
    "--alpha-regularization",
    "0.01",
    "--ray-address",
    "127.0.0.1:6390",
]
REFERENCE_SCOPE = (
    "config quadratic-minimal.yaml; targets homogeneous; potential Quadratic; m 1e-05 Mp; "
    "N_init 20–20, 1 sample; N_final 5–5, 1 sample; delta_Nstar 0.1–3, 10 samples; "
    "n_collocation_points 5; alpha_regularization 0.01; 10 shards; "
    "job rrk-adoption-04-reference"
)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Case:
    """A temporary directory holding the stand-in, the database path (never created here) and the
    runs root."""

    def __init__(self, tmp_path, request):
        # resolved: on macOS the temporary directory is reached through /var -> /private/var
        self.top = Path(tmp_path).resolve()
        self.runs_root = self.top / "runs"
        self.runs_root.mkdir()
        self.database = self.top / "store.sqlite"
        self.addcleanup = request.addfinalizer

    def program(self, behaviour="return"):
        return standin_program(self.top, behaviour, self.runs_root)

    def run_it(self, behaviour="return", argv=None, **kwargs):
        program = self.program(behaviour)
        argv = wrapper_argv(self.database) if argv is None else argv
        done = in_process(self.addcleanup, program, argv, self.runs_root, **kwargs)
        return program, argv, done


@pytest.fixture
def case(tmp_path, request):
    return Case(tmp_path, request)


class TestRegistration:
    def test_the_manifest_is_written_before_the_programs_first_line(self, case):
        program, _, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        run = only_run(case.runs_root)
        assert read_record(program)["manifests_at_start"] == [str(run / "manifest.json")]

    def test_the_manifest_records_the_program_the_store_the_scope_and_the_packages(
        self, case
    ):
        program, _, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        manifest = read_json(only_run(case.runs_root) / "manifest.json")

        # P4: the program run, with its own hash. A stand-in outside the client root is recorded
        # by its absolute path, as is a store outside it (begin's _repo_path)
        assert manifest["script"] == str(program)
        assert manifest["script_sha256"] == sha256(program)
        assert manifest["results"] == str(case.database)
        assert manifest["checkpoint"] is None
        # begin takes git_head and git_dirty from the directory of `script` (runregistrykit
        # v0.2.0, begin): the stand-in's temporary directory is in no repository.
        # TestRegisterInProduction shows the production form
        assert manifest["git_head"] == "unknown"
        assert manifest["git_dirty"] is False
        assert manifest["scope"] == (
            "no config file; targets homogeneous; potential Quadratic; "
            "m 10^-6–10^-5 Mp, 10 per decade; N_init 20–20, 1 sample; "
            "N_final 5–5, 1 sample; delta_Nstar 0.1–3, 10 samples; 20 shards; no job name"
        )
        assert (manifest["campaign"], manifest["prompt"]) == ("rrk-adoption", "03")
        assert only_run(case.runs_root).name.startswith("rrk-adoption-03-unit-")
        for name in ("runregistrykit", "datastorekit", "raypoolkit"):
            assert name in manifest["packages"]
            assert manifest["packages"][name] is not None, name

    def test_heartbeat_means_states_the_floor_the_interval_and_the_gradient_branch(
        self, case
    ):
        _, _, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        said = read_json(only_run(case.runs_root) / "manifest.json")["heartbeat_means"]
        assert said == registered_run.HEARTBEAT_MEANS.format(
            interval=registered_run.BEAT_MIN_INTERVAL,
            notify_min=registered_run.NOTIFY_MIN_INTERVAL,
            notify_time=registered_run.NOTIFY_TIME_INTERVAL,
            notify_batch=registered_run.NOTIFY_BATCH_SIZE,
            stale=runregistrykit.DEFAULT_STALE_AFTER,
        )
        for fragment in (
            "at most once per 30 s",
            "or at once when the line changes the stage",
            "only after ray.wait has returned completed work",
            "never sooner than 60 s after its last one",
            "once 300 s have passed",
            "more than 500 queue events",
            "within about five minutes",
            "(title=None)",
            "a worker's line beats too",
            "does NOT mean any Ray task or actor is progressing",
            "(900 s, `list --stale-after`)",
            "the gradient branch's solves have run for hours",
            "Stale means go and look",
        ):
            assert fragment in said

    def test_the_manifests_argv_is_the_wrappers(self, case):
        _, argv, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        manifest = read_json(only_run(case.runs_root) / "manifest.json")
        assert manifest["argv"][0] == str(WRAPPER)
        assert manifest["argv"][1:] == argv

    def test_it_prints_the_run_id_the_manifest_and_the_list_command(self, case):
        _, _, done = case.run_it()
        run = only_run(case.runs_root)
        lines = done.out.text().splitlines()
        assert lines[0] == f">> registered_run: registered as {run.name}"
        assert lines[1] == f">>   manifest {run / 'manifest.json'}"
        assert lines[2] == ">>   list it with: ./venv/bin/python -m runregistrykit list"
        # and stdout.log holds them, as everything else the run wrote
        assert (run / "stdout.log").read_text().splitlines()[:3] == lines[:3]


class TestTheProgram:
    """What the program sees: its own path as `sys.argv[0]`, `main.py`'s arguments verbatim,
    `__name__ == "__main__"`, and `ray.init` called with its arguments unchanged (ChamPBH's note 03,
    ruling 5)."""

    def test_it_runs_as_main_from_its_own_file_with_main_pys_arguments(self, case):
        program, argv, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        record = read_record(program)
        assert record["argv"][0] == str(program)
        assert record["argv"][1:] == argv[argv.index("--") + 1 :]
        assert record["name"] == "__main__"
        assert record["file"] == str(program)

    def test_ray_init_gets_the_programs_arguments_unchanged(self, case):
        _, _, done = case.run_it()
        assert done.init.calls == [((), {"address": ADDRESS})]
        assert len(done.shutdown.calls) == 1

    def test_the_wrappers_handler_replaces_rays_after_ray_init(self, case):
        seen = []

        def like_ray(*args, **kwargs):
            install_ray_like_handler()
            seen.append(signal.getsignal(signal.SIGTERM))

        program, _, done = case.run_it(init=Recorder(side_effect=like_ray))
        assert done.outcome is None, repr(done.outcome)
        assert seen == [ray_like_sigterm_handler]
        record = read_record(program)
        assert record["sigterm_before_init"] == "register.<locals>.terminal"
        assert record["sigterm_after_init"] == "make_killed_handler.<locals>.killed_handler"

    def test_a_returning_program_is_done_at_its_last_stage(self, case):
        _, _, done = case.run_it()
        assert done.outcome is None, repr(done.outcome)
        run = only_run(case.runs_root)
        status = read_json(run / "status.json")
        assert (status["state"], status["exit_code"]) == ("done", 0)
        assert status["stage"] == f"{TITLE}, all work items complete"
        # there is no store, so no fingerprint: recorded, and the run is still done
        assert "does not exist" in status["fingerprint_error"]
        assert not case.database.exists()
        # the real stream and the copy hold the same text, byte for byte
        assert (run / "stdout.log").read_text() == done.out.text()
        assert done.taken == {"stdout": True, "stderr": True, "handlers": True}


class TestRegisterInProduction:
    """P4 in its production form: `register` with `program=MAIN_PY` records `main.py`, its hash and
    this repository's `HEAD`. Nothing runs: `register` reads no `main.py` text and starts nothing
    (ChamPBH's note 03, ruling 4). Its three lines set no stage (the orchestrator's note for 03,
    correction 4)."""

    def test_the_script_is_main_py_with_its_hash_and_this_repositorys_head(
        self, case, request
    ):
        argv = wrapper_argv(case.database, slug="production")
        args, _, parsed, defaulted = registered_run.parse_arguments(argv)
        saved = TakeOver()
        request.addfinalizer(saved.restore)
        out = StringWriter()
        sys.stdout, sys.stderr = out, StringWriter()
        try:
            run = registered_run.register(
                args,
                parsed,
                argv,
                defaulted=defaulted,
                program=registered_run.MAIN_PY,
                runs_root=case.runs_root,
            )
            # observed before restoring
            taken = (
                isinstance(sys.stdout, registered_run.RegisteredStream),
                isinstance(sys.stderr, registered_run.RegisteredStream),
                signal.getsignal(signal.SIGTERM).__qualname__,
                signal.getsignal(signal.SIGINT).__qualname__,
            )
        finally:
            saved.restore()
        assert taken == (
            True,
            True,
            "register.<locals>.terminal",
            "register.<locals>.terminal",
        )
        manifest = read_json(run.manifest_path)
        assert manifest["script"] == "main.py"
        assert manifest["script_sha256"] == sha256(REPO_ROOT / "main.py")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert manifest["git_head"] == head
        assert manifest["results"] == str(case.database)
        assert Path(run.path).parent == case.runs_root
        status = read_json(run.status_path)
        assert status["state"] == "running"
        # the registration lines reached the stream and the copy, and set no stage
        assert out.text().splitlines()[0].startswith(">> registered_run: registered as ")
        assert len((Path(run.path) / "stdout.log").read_text().splitlines()) == 3
        assert status.get("stage") is None


class TestScope:
    """`scope` is one line from `main.py`'s parsed arguments as given, never its grid (ChamPBH's
    note 03, ruling 11; the orchestrator's note for 03, "Scope")."""

    def scope(self, main_args):
        _, _, parsed, defaulted = registered_run.parse_arguments(
            wrapper_argv(None, main_args=main_args)
        )
        return registered_run.describe_scope(parsed, defaulted)

    def test_the_scope_of_04s_reference(self):
        assert self.scope(REFERENCE) == REFERENCE_SCOPE

    def test_more_than_six_values_read_as_a_count_and_a_range(self):
        scope = self.scope(
            [
                "--database",
                "x.sqlite",
                "--ray-address",
                ADDRESS,
                "--potential-type",
                "Quartic",
                "--lambda-values",
                *["1e-14", "2e-14", "5e-14", "1e-13", "2e-13", "5e-13", "1e-12"],
                "--sample-grid-csv",
                "grid.csv",
                "--targets",
                "homogeneous",
                "gradient",
                "--no-store-values",
                "--stop-after",
                "full-instanton",
                "--shards",
                "4",
                "--job-name",
                "a-job",
            ]
        )
        assert scope == (
            "no config file; targets homogeneous, gradient; potential Quartic; "
            "lambda 7 values, 1e-14–1e-12; sample grid grid.csv; --no-store-values; "
            "stop after full-instanton; 4 shards; job a-job"
        )

    def test_a_value_equal_to_the_default_is_still_given(self):
        # 04's --alpha-regularization 0.01 is the parser's default, and is given
        scope = self.scope(
            ["--database", "x.sqlite", "--ray-address", ADDRESS]
            + ["--alpha-regularization", "0.01"]
        )
        assert "alpha_regularization 0.01" in scope
        assert "n_collocation_points" not in scope


class TestBeginsErrors:
    """A `ConfigError` from `begin` keeps its type and its traceback; any other `RuntimeError` from
    it becomes a `Refusal` with its text. Either way nothing is created and nothing is taken over,
    and the program does not run."""

    def test_a_config_error_is_not_a_refusal(self, case):
        error = runregistrykit.ConfigError("no runregistrykit.toml was found")
        assert isinstance(error, RuntimeError)
        with mock.patch.object(runregistrykit, "begin", side_effect=error):
            program, _, done = case.run_it()
        assert done.outcome is error
        assert not isinstance(done.outcome, registered_run.Refusal)
        assert list(case.runs_root.iterdir()) == []
        assert not program.with_suffix(".json").exists(), "the program ran"
        assert done.taken == {"stdout": False, "stderr": False, "handlers": False}
        assert done.init.calls == []

    def test_a_runtime_error_is_a_refusal_with_its_text(self, case):
        error = RuntimeError("Cannot begin run x: ... No run directory was created")
        with mock.patch.object(runregistrykit, "begin", side_effect=error):
            program, _, done = case.run_it()
        assert isinstance(done.outcome, registered_run.Refusal)
        assert str(done.outcome) == str(error)
        assert done.outcome.__cause__ is error
        assert list(case.runs_root.iterdir()) == []
        assert not program.with_suffix(".json").exists(), "the program ran"
        assert done.taken == {"stdout": False, "stderr": False, "handlers": False}
