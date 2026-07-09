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

"""
Golden-run regression test for prompt P1
(.prompts/gradient-coupled-plotting/05-P1-extract-plotting-machinery.md):
move reusable plotting machinery out of plot_InstantonSolutions.py into the
new `plotting/` package, with zero behaviour change.

The prompt's own acceptance test describes running
`plot_InstantonSolutions.py` against `quadratic-minimal.yaml` before/after
this change on a fixed pre-populated database, and diffing every output file
byte-for-byte. That requires a live Ray cluster and a real, already-populated
SQLite datastore (see CLAUDE.md: "Ray must be running") -- there is no
"before" snapshot to diff against in an automated, from-scratch test run,
and as tests/test_compaction_scalars_refactor_golden.py's own docstring
notes, this codebase's convention for this class of "pure refactor, prove no
behaviour changed" acceptance test is instead to exercise the moved code
directly, bypassing Ray/the datastore where the moved functions allow it.

This test applies that convention at the exact seam P1 touches:

1. **Identity, not duplication.** Every function this prompt moves must be
   re-exported into `plot_InstantonSolutions`'s namespace via `import`, not
   redefined -- so `plot_InstantonSolutions._foo is plotting.<module>._foo`
   for every moved `_foo`. This is the strongest guard against the "copy
   instead of move" failure mode: a copy would still pass every other check
   below but fail this one the moment the two definitions drift.
2. **Byte-for-byte behaviour of every moved pure function**, exercised
   directly against fixed inputs with hand-computed expected outputs (the
   direct analogue of a byte-for-byte diff, at the function level rather
   than the rendered-file level).
3. **The two new generic helpers added by this prompt**
   (`plotting.dispatch._render_item`, `plotting.fetch.fetch_over_grid`),
   which are pure additions with no "before" state to diff against, so they
   get ordinary behavioural unit tests instead.
"""

import matplotlib

matplotlib.use("Agg")

import ray
import pytest
from matplotlib import pyplot as plt

import plot_InstantonSolutions as driver
import plotting.annotations as annotations
import plotting.dispatch as dispatch
import plotting.fetch as fetch
import plotting.provenance as provenance
import plotting.sampling as sampling


@pytest.fixture(scope="module", autouse=True)
def _ray_ready():
    """These tests exercise `ray.put`/`ray.get` (via FullInstantonProxy /
    SlowRollInstantonProxy construction and the generic fetch/dispatch
    helpers) but need none of ShardedPool's actors or a SQLite database, so
    a bare local Ray init is enough -- no `live_pool` fixture, no
    `@pytest.mark.integration`. Does not call ray.shutdown(): other test
    modules in the same session may still need Ray, and conftest.py's
    session-scoped `live_pool` fixture already owns shutdown at session end.
    """
    ray.init(ignore_reinit_error=True)
    yield


# ---------------------------------------------------------------------------
# 1. Re-point, don't duplicate: the driver module must hold the SAME function
#    objects as the new plotting.* modules, not independent copies.
# ---------------------------------------------------------------------------


class TestDriverReExportsAreIdentical:
    def test_provenance(self):
        assert driver._provenance_footer is provenance._provenance_footer
        assert driver.VERSION_LABEL is provenance.VERSION_LABEL

    def test_annotations(self):
        assert driver._extract_cf_annotation is annotations._extract_cf_annotation
        assert driver._cf_annotation_text is annotations._cf_annotation_text
        assert driver._add_cf_annotation is annotations._add_cf_annotation

    def test_sampling(self):
        assert driver._evenly_sample is sampling._evenly_sample
        assert driver._safe_name is sampling._safe_name
        assert driver._safe_num is sampling._safe_num

    def test_dispatch(self):
        assert driver._dispatch_plot_work is dispatch._dispatch_plot_work

    def test_fetch(self):
        assert driver._instanton_key_payload is fetch._instanton_key_payload
        assert driver._cf_key_payload is fetch._cf_key_payload
        assert driver._qualifying_action is fetch._qualifying_action
        assert driver._extract_cf_summary is fetch._extract_cf_summary
        assert driver._cf_vectorized_fetch is fetch._cf_vectorized_fetch

    def test_no_local_redefinitions_remain(self):
        """Guard against a future edit reintroducing a local copy: every
        moved name in the driver module's own __dict__ must trace back to
        the plotting.* module it was moved to, via __module__."""
        moved = {
            "_provenance_footer": provenance,
            "_extract_cf_annotation": annotations,
            "_cf_annotation_text": annotations,
            "_add_cf_annotation": annotations,
            "_evenly_sample": sampling,
            "_safe_name": sampling,
            "_safe_num": sampling,
            "_dispatch_plot_work": dispatch,
            "_instanton_key_payload": fetch,
            "_cf_key_payload": fetch,
            "_qualifying_action": fetch,
            "_extract_cf_summary": fetch,
            "_cf_vectorized_fetch": fetch,
        }
        for name, module in moved.items():
            fn = getattr(driver, name)
            assert fn.__module__ == module.__name__, (
                f"{name} appears to be locally redefined in "
                f"plot_InstantonSolutions.py rather than imported from "
                f"{module.__name__}"
            )


# ---------------------------------------------------------------------------
# 2. Byte-for-byte behaviour of moved pure functions.
# ---------------------------------------------------------------------------


class TestSamplingHelpers:
    def test_evenly_sample_returns_everything_when_n_leq_k(self):
        assert sampling._evenly_sample([1, 2, 3], 5) == [1, 2, 3]
        assert sampling._evenly_sample([1, 2, 3], 3) == [1, 2, 3]

    def test_evenly_sample_subsamples_by_index(self):
        seq = list(range(10))
        result = sampling._evenly_sample(seq, 4)
        assert result == [0, 3, 6, 9]

    def test_safe_name_strips_special_characters(self):
        assert sampling._safe_name("quadratic (m=1e-5)") == "quadratic_m=1e-5"
        assert sampling._safe_name("a, b") == "a_b"

    def test_safe_num_formats_floats(self):
        assert sampling._safe_num(1.2345678) == "1p235"
        assert sampling._safe_num(-0.5) == "m0p5"
        assert sampling._safe_num(0.0) == "0"


class _UnitsStub:
    Mpc = 2.0
    SolarMass = 5.0


class _CFStub:
    def __init__(self, available=True, failure=False, tag=None, **kwargs):
        self.available = available
        self.failure = failure
        self.tag = tag
        self.C_threshold = kwargs.get("C_threshold", 0.4)
        for key in (
            "C_peak_full",
            "C_bar_peak_full",
            "r_max_full",
            "r_peak_full",
            "M_max_full",
            "M_peak_full",
            "C_peak_slow_roll",
            "C_bar_peak_slow_roll",
            "r_max_slow_roll",
            "r_peak_slow_roll",
            "M_max_slow_roll",
            "M_peak_slow_roll",
        ):
            setattr(self, key, kwargs.get(key))


_FULL_CF = _CFStub(
    C_peak_full=0.5,
    C_bar_peak_full=0.3,
    r_max_full=10.0,
    r_peak_full=4.0,
    M_max_full=15.0,
    M_peak_full=25.0,
    C_peak_slow_roll=0.45,
    C_bar_peak_slow_roll=0.28,
    r_max_slow_roll=8.0,
    r_peak_slow_roll=3.0,
    M_max_slow_roll=10.0,
    M_peak_slow_roll=20.0,
)


class TestAnnotationHelpers:
    def test_extract_cf_annotation_none_cases(self):
        assert annotations._extract_cf_annotation(None, _UnitsStub()) is None
        assert (
            annotations._extract_cf_annotation(
                _CFStub(available=False), _UnitsStub()
            )
            is None
        )
        assert (
            annotations._extract_cf_annotation(_CFStub(failure=True), _UnitsStub())
            is None
        )

    def test_extract_cf_annotation_applies_unit_conversion(self):
        ann = annotations._extract_cf_annotation(_FULL_CF, _UnitsStub())
        assert ann["C_peak_full"] == 0.5
        assert ann["r_max_full_Mpc"] == pytest.approx(5.0)  # 10.0 / 2.0
        assert ann["r_peak_full_Mpc"] == pytest.approx(2.0)  # 4.0 / 2.0
        assert ann["M_max_full_solar"] == pytest.approx(3.0)  # 15.0 / 5.0
        assert ann["M_peak_full_solar"] == pytest.approx(5.0)  # 25.0 / 5.0
        assert ann["r_max_slow_roll_Mpc"] == pytest.approx(4.0)  # 8.0 / 2.0
        assert ann["M_max_slow_roll_solar"] == pytest.approx(2.0)  # 10.0 / 5.0

    def test_cf_annotation_text_none_and_populated(self):
        assert annotations._cf_annotation_text(None) is None
        ann = annotations._extract_cf_annotation(_FULL_CF, _UnitsStub())
        text = annotations._cf_annotation_text(ann)
        assert "Full:" in text
        assert "SR:" in text
        assert r"$C_{\rm peak}$=0.5" in text
        assert r"$r_{\rm max}$=5 Mpc" in text

    def test_add_cf_annotation_no_text_still_lays_out_figure(self):
        fig = plt.figure()
        annotations._add_cf_annotation(fig, None)
        plt.close(fig)

    def test_add_cf_annotation_renders_text_on_figure(self):
        fig = plt.figure()
        annotations._add_cf_annotation(fig, "line one\nline two")
        rendered = [t.get_text() for t in fig.texts]
        assert "line one\nline two" in rendered
        plt.close(fig)


class TestProvenanceFooter:
    def test_stamps_version_and_timestamp(self):
        fig = plt.figure()
        provenance._provenance_footer(fig)
        rendered = "\n".join(t.get_text() for t in fig.texts)
        assert f"StochasticInstanton v{provenance.VERSION_LABEL}" in rendered
        plt.close(fig)

    def test_includes_run_label_as_first_line(self):
        fig = plt.figure()
        provenance._provenance_footer(fig, run_label="mydb.sqlite  |  cfg.yaml")
        rendered = "\n".join(t.get_text() for t in fig.texts)
        assert "mydb.sqlite  |  cfg.yaml" in rendered
        plt.close(fig)

    def test_introspects_object_attributes(self):
        class _Obj:
            available = True
            store_id = 42
            atol = 1e-8
            rtol = 1e-9

        fig = plt.figure()
        provenance._provenance_footer(fig, _Obj())
        rendered = "\n".join(t.get_text() for t in fig.texts)
        assert "id=42" in rendered
        assert "atol=1e-08" in rendered
        plt.close(fig)

    def test_never_raises_on_missing_attributes(self):
        fig = plt.figure()
        provenance._provenance_footer(fig, object())
        plt.close(fig)


class TestKeyPayloadHelpers:
    def test_instanton_key_payload_shape(self):
        payload = fetch._instanton_key_payload(
            "traj-sentinel", 60.0, 10.0, 5.0, 1e-8, 1e-9, "dm-sentinel"
        )
        assert payload == dict(
            trajectory="traj-sentinel",
            N_init=60.0,
            N_final=10.0,
            delta_Nstar=5.0,
            atol=1e-8,
            rtol=1e-9,
            tags=[],
            diffusion_model="dm-sentinel",
        )

    def test_cf_key_payload_shape(self):
        payload = fetch._cf_key_payload(
            "traj-sentinel", "fi-sentinel", "sri-sentinel", 5.0, "cosmo-sentinel",
            1e-8, 1e-9,
        )
        assert payload == dict(
            trajectory="traj-sentinel",
            full_instanton="fi-sentinel",
            slow_roll_instanton="sri-sentinel",
            delta_Nstar=5.0,
            cosmo="cosmo-sentinel",
            C_threshold=0.4,
            atol=1e-8,
            rtol=1e-9,
            tags=[],
        )


class _InstStub:
    """Duck-typed stand-in for a FullInstanton/SlowRollInstanton, exposing
    just the attributes FullInstantonProxy/SlowRollInstantonProxy read in
    their constructors (store_id, available, N_init_value, N_final_value,
    delta_Nstar) plus msr_action for _qualifying_action."""

    def __init__(self, available, store_id=1, msr_action=None):
        self.available = available
        self.store_id = store_id if available else None
        self.msr_action = msr_action
        self.failure = False
        self.N_init_value = 60.0
        self.N_final_value = 10.0
        self.delta_Nstar = 5.0


class TestQualifyingActionAndSummary:
    def test_qualifying_action(self):
        assert fetch._qualifying_action(None) is None
        assert fetch._qualifying_action(_InstStub(available=False)) is None
        assert fetch._qualifying_action(_InstStub(available=True, msr_action=3.14)) == 3.14

    def test_extract_cf_summary_none_cases(self):
        none12 = (None,) * 12
        assert fetch._extract_cf_summary(None, _UnitsStub()) == none12
        assert (
            fetch._extract_cf_summary(_CFStub(available=False), _UnitsStub())
            == none12
        )

    def test_extract_cf_summary_applies_unit_conversion(self):
        s = fetch._extract_cf_summary(_FULL_CF, _UnitsStub())
        assert s == (
            0.5,
            0.3,
            pytest.approx(3.0),  # M_max_full / SolarMass
            pytest.approx(5.0),  # M_peak_full / SolarMass
            0.45,
            0.28,
            pytest.approx(2.0),  # M_max_slow_roll / SolarMass
            pytest.approx(4.0),  # M_peak_slow_roll / SolarMass
            pytest.approx(5.0),  # r_max_full / Mpc
            pytest.approx(2.0),  # r_peak_full / Mpc
            pytest.approx(4.0),  # r_max_slow_roll / Mpc
            pytest.approx(1.5),  # r_peak_slow_roll / Mpc
        )


class _StubPool:
    """Minimal stand-in for ShardedPool's vectorized-fetch API: records every
    call and returns a canned, ray.put-wrapped response."""

    def __init__(self, response_by_call=None, single_response=None):
        self.calls = []
        self._response_by_call = response_by_call
        self._single_response = single_response

    def object_get_vectorized(self, class_name, shard_key, payload_data):
        self.calls.append((class_name, shard_key, payload_data))
        if self._response_by_call is not None:
            response = self._response_by_call[len(self.calls) - 1]
        else:
            response = self._single_response
        return ray.put(response)


class TestCfVectorizedFetch:
    def test_reassembles_index_aligned_results_with_gaps(self):
        # Position 0: fi available -> queried. Position 1: only sri available
        # -> queried. Position 2: neither available -> skipped (None, no
        # datastore round-trip).
        fi_list = [_InstStub(available=True), _InstStub(available=False), None]
        sri_list = [None, _InstStub(available=True), None]

        # Tagged (rather than compared by identity) because the stub pool
        # round-trips these through ray.put/ray.get, same as a real
        # ShardedPool actor call would -- the returned objects are
        # deserialised copies, not the same Python objects.
        cfA, cfB = _CFStub(tag="A"), _CFStub(tag="B")
        pool = _StubPool(single_response=[cfA, cfB])

        result = fetch._cf_vectorized_fetch(
            pool, "traj-proxy-sentinel", fi_list, sri_list, 5.0, "cosmo-sentinel",
            1e-8, 1e-9,
        )

        assert [r.tag if r is not None else None for r in result] == ["A", "B", None]
        assert len(pool.calls) == 1
        class_name, shard_key, payload_data = pool.calls[0]
        assert class_name == "CompactionFunction"
        assert shard_key == 5.0
        assert len(payload_data) == 2
        assert all(p["_do_not_populate"] is True for p in payload_data)

    def test_no_available_instantons_skips_the_datastore_entirely(self):
        fi_list = [_InstStub(available=False)]
        sri_list = [None]
        pool = _StubPool(single_response=[])

        result = fetch._cf_vectorized_fetch(
            pool, "traj-proxy-sentinel", fi_list, sri_list, 5.0, "cosmo-sentinel",
            1e-8, 1e-9,
        )

        assert result == [None]
        assert pool.calls == []


# ---------------------------------------------------------------------------
# 3. New generic helpers added by this prompt (pure additions; no "before"
#    behaviour to diff against, so these are ordinary unit tests).
# ---------------------------------------------------------------------------


class TestFetchOverGridGeneric:
    def test_bins_by_shard_key_and_reassembles_in_input_order(self):
        items = [
            {"shard": "a", "id": 1},
            {"shard": "b", "id": 2},
            {"shard": "a", "id": 3},
        ]

        class _ShardedStubPool:
            def __init__(self):
                self.calls = []

            def object_get_vectorized(self, class_name, shard_key, payload_data):
                self.calls.append((class_name, shard_key, payload_data))
                response = [f"result-for-{p['id']}" for p in payload_data]
                return ray.put(response)

        pool = _ShardedStubPool()
        result = fetch.fetch_over_grid(
            pool,
            "Foo",
            shard_key_of=lambda it: it["shard"],
            key_payload_of=lambda it: {"id": it["id"]},
            items=items,
        )

        assert result == ["result-for-1", "result-for-2", "result-for-3"]
        # One vectorized call per distinct shard key, not per item.
        assert len(pool.calls) == 2
        shard_keys_called = {call[1] for call in pool.calls}
        assert shard_keys_called == {"a", "b"}
        for _, _, payload_data in pool.calls:
            assert all(p["_do_not_populate"] is True for p in payload_data)

    def test_do_not_populate_flag_propagates(self):
        class _RecordingStubPool:
            def __init__(self):
                self.seen_payloads = []

            def object_get_vectorized(self, class_name, shard_key, payload_data):
                self.seen_payloads.extend(payload_data)
                return ray.put([None for _ in payload_data])

        pool = _RecordingStubPool()
        fetch.fetch_over_grid(
            pool,
            "Foo",
            shard_key_of=lambda it: "only-shard",
            key_payload_of=lambda it: {"id": it},
            items=[1, 2],
            do_not_populate=False,
        )
        assert all(p["_do_not_populate"] is False for p in pool.seen_payloads)


class TestRenderItemGeneric:
    """`_render_item` is a `@ray.remote` function whose body is only ever
    meant to run inside a genuine Ray worker process. Those worker processes
    import task arguments by module reference, which only works for objects
    reachable via a real package import -- not for classes/functions defined
    directly in a pytest-collected test file (`tests/` has no __init__.py,
    so pytest's own sys.path insertion for it is invisible to worker
    subprocesses). So instead of dispatching a real `.remote()` call, this
    exercises `_render_item`'s actual body via the `RemoteFunction._function`
    escape hatch (the same undecorated callable Ray itself invokes inside
    the worker) -- verifying its logic without needing worker-side imports.
    """

    def test_is_a_ray_remote_function(self):
        assert hasattr(dispatch._render_item, "remote")

    def test_body_sets_theme_and_calls_figure_fn(self, tmp_path):
        calls = []

        def figure_fn(payload, output_dir, fmt, run_label=""):
            calls.append((payload, output_dir, fmt, run_label))

        dispatch._render_item._function(
            figure_fn, "payload-42", str(tmp_path), "txt", "run-label"
        )

        assert calls == [("payload-42", tmp_path, "txt", "run-label")]


class TestDispatchConventionPreserved:
    """`_dispatch_plot_work` only needs `remote_fn.remote(*args)` to be
    callable, so a fake stand-in for a RemoteFunction exercises the exact
    (remote_fn, args) unpacking convention without going through a real
    cross-process Ray dispatch (which, like `_render_item` above, would
    require the worker to import this pytest-collected test module)."""

    def test_remote_fn_args_tuple_convention(self):
        class _FakeRemoteFn:
            def __init__(self):
                self.calls = []

            def remote(self, *args):
                self.calls.append(args)
                return sum(args)

        fake = _FakeRemoteFn()
        result = dispatch._dispatch_plot_work((fake, (2, 3)))
        assert fake.calls == [(2, 3)]
        assert result == 5
