"""
Unit tests for config/grid_builder.py.

Tests cover:
  (a) build_cartesian_grid matches itertools.product for a small synthetic input
  (b) build_grid_from_csv produces len(model_list) * len(csv_rows) tuples with
      correct (model_idx, N_init_obj, N_final_obj, dns_obj) structure — model
      varies, CSV rows are NOT crossed against each other
  (c) Each malformed-CSV error case: missing column, non-numeric value, empty
      file, header-only (no data rows)
"""

import itertools
import io
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from config.grid_builder import (
    _read_csv,
    build_cartesian_grid,
    build_grid_from_csv,
    build_instanton_grid,
)


# ---------------------------------------------------------------------------
# Synthetic domain-object stub
# ---------------------------------------------------------------------------

class _Obj:
    """Minimal stub for N_init / N_final / delta_Nstar domain objects."""
    def __init__(self, value):
        self.value = value
    def __float__(self):
        return float(self.value)
    def __eq__(self, other):
        return isinstance(other, _Obj) and self.value == other.value
    def __hash__(self):
        return hash(self.value)
    def __repr__(self):
        return f"Obj({self.value})"


def _make_objs(*values):
    return [_Obj(v) for v in values]


# ---------------------------------------------------------------------------
# (a) build_cartesian_grid
# ---------------------------------------------------------------------------

class TestBuildCartesianGrid:
    def setup_method(self):
        self.model_list = [{"label": "A"}, {"label": "B"}]
        self.N_init_array  = _make_objs(20.0, 25.0)
        self.N_final_array = _make_objs(5.0)
        self.dns_array     = _make_objs(0.5, 1.0, 2.0)

    def test_matches_itertools_product(self):
        expected = list(
            itertools.product(
                range(len(self.model_list)),
                self.N_init_array,
                self.N_final_array,
                self.dns_array,
            )
        )
        result = build_cartesian_grid(
            self.model_list,
            self.N_init_array,
            self.N_final_array,
            self.dns_array,
        )
        assert result == expected

    def test_length(self):
        result = build_cartesian_grid(
            self.model_list,
            self.N_init_array,
            self.N_final_array,
            self.dns_array,
        )
        expected_len = (
            len(self.model_list)
            * len(self.N_init_array)
            * len(self.N_final_array)
            * len(self.dns_array)
        )
        assert len(result) == expected_len

    def test_tuple_structure(self):
        result = build_cartesian_grid(
            self.model_list,
            self.N_init_array,
            self.N_final_array,
            self.dns_array,
        )
        for tup in result:
            assert len(tup) == 4
            model_idx, N_init, N_final, dns = tup
            assert isinstance(model_idx, int)
            assert 0 <= model_idx < len(self.model_list)

    def test_empty_model_list(self):
        result = build_cartesian_grid([], self.N_init_array, self.N_final_array, self.dns_array)
        assert result == []

    def test_single_point(self):
        result = build_cartesian_grid(
            [{"label": "M"}], _make_objs(20.0), _make_objs(5.0), _make_objs(1.0)
        )
        assert len(result) == 1
        assert result[0] == (0, _make_objs(20.0)[0], _make_objs(5.0)[0], _make_objs(1.0)[0])


# ---------------------------------------------------------------------------
# Helpers for CSV-path tests
# ---------------------------------------------------------------------------

def _write_csv(content: str) -> str:
    """Write content to a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def _mock_pool_and_ray(rows):
    """
    Return (pool_mock, ray_get_patch) that make build_grid_from_csv work
    without a real Ray cluster.

    pool.object_get("N_init"|"N_final"|"delta_Nstar", payload_data=[...])
    returns a plain list of _Obj stubs keyed on the float value.

    ray.get([ref1, ref2, ref3]) is patched to return its argument unchanged,
    since the "refs" are already resolved lists.
    """
    def _pool_object_get(cls_name, payload_data=None, **kwargs):
        return [_Obj(row["value"]) for row in payload_data]

    pool = MagicMock()
    pool.object_get.side_effect = _pool_object_get
    return pool


# ---------------------------------------------------------------------------
# (b) build_grid_from_csv — correct structure and crossing
# ---------------------------------------------------------------------------

class TestBuildGridFromCsv:
    CSV_CONTENT = "N_init,N_final,delta_Nstar\n20.0,5.0,0.5\n25.0,5.0,1.0\n"

    def setup_method(self):
        self.model_list = [{"label": "A"}, {"label": "B"}, {"label": "C"}]
        self.csv_path = _write_csv(self.CSV_CONTENT)

    def teardown_method(self):
        os.unlink(self.csv_path)

    def _run(self):
        pool = _mock_pool_and_ray([])
        with patch("config.grid_builder.ray.get", new=lambda x: x):
            return build_grid_from_csv(pool, self.csv_path, self.model_list)

    def test_total_tuple_count(self):
        result = self._run()
        # 3 models × 2 CSV rows = 6 tuples
        assert len(result) == 3 * 2

    def test_tuple_structure(self):
        result = self._run()
        for tup in result:
            assert len(tup) == 4

    def test_model_index_range(self):
        result = self._run()
        model_indices = [t[0] for t in result]
        assert sorted(set(model_indices)) == list(range(len(self.model_list)))

    def test_csv_rows_not_crossed_against_each_other(self):
        """Each CSV row appears exactly len(model_list) times — no row × row cross."""
        result = self._run()
        # Collect unique (N_init_value, N_final_value, dns_value) combos
        triples = set((float(t[1]), float(t[2]), float(t[3])) for t in result)
        # Should be exactly 2 unique triples (the 2 CSV rows)
        assert len(triples) == 2
        assert (20.0, 5.0, 0.5) in triples
        assert (25.0, 5.0, 1.0) in triples

    def test_each_triple_appears_once_per_model(self):
        result = self._run()
        from collections import Counter
        triple_counts = Counter(
            (float(t[1]), float(t[2]), float(t[3])) for t in result
        )
        for count in triple_counts.values():
            assert count == len(self.model_list)

    def test_pool_called_with_correct_payload(self):
        pool = _mock_pool_and_ray([])
        with patch("config.grid_builder.ray.get", new=lambda x: x):
            build_grid_from_csv(pool, self.csv_path, self.model_list)
        # Verify pool.object_get was called for all three types
        calls = {c.args[0] for c in pool.object_get.call_args_list}
        assert "N_init" in calls
        assert "N_final" in calls
        assert "delta_Nstar" in calls

    def test_duplicate_csv_rows_dont_add_extra_tuples(self):
        """Duplicate CSV rows resolve to the same objects — grid length unchanged."""
        dup_content = "N_init,N_final,delta_Nstar\n20.0,5.0,0.5\n20.0,5.0,0.5\n"
        path = _write_csv(dup_content)
        try:
            pool = _mock_pool_and_ray([])
            with patch("config.grid_builder.ray.get", new=lambda x: x):
                result = build_grid_from_csv(pool, path, self.model_list)
            # 3 models × 2 rows (even if duplicate) = 6 tuples in grid list
            # (dedup happens at pool level, not here)
            assert len(result) == 3 * 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# (c) Malformed CSV error cases
# ---------------------------------------------------------------------------

class TestReadCsvErrors:
    def test_missing_column(self):
        path = _write_csv("N_init,N_final\n20.0,5.0\n")
        try:
            with pytest.raises(ValueError, match="missing required column"):
                _read_csv(path)
        finally:
            os.unlink(path)

    def test_missing_multiple_columns(self):
        path = _write_csv("N_init\n20.0\n")
        try:
            with pytest.raises(ValueError, match="missing required column"):
                _read_csv(path)
        finally:
            os.unlink(path)

    def test_non_numeric_value(self):
        path = _write_csv("N_init,N_final,delta_Nstar\n20.0,five,0.5\n")
        try:
            with pytest.raises(ValueError, match="non-numeric value"):
                _read_csv(path)
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = _write_csv("")
        try:
            with pytest.raises(ValueError, match="empty"):
                _read_csv(path)
        finally:
            os.unlink(path)

    def test_header_only_no_data_rows(self):
        path = _write_csv("N_init,N_final,delta_Nstar\n")
        try:
            with pytest.raises(ValueError, match="no data rows"):
                _read_csv(path)
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(ValueError, match="Cannot open CSV file"):
            _read_csv("/nonexistent/path/to/file.csv")

    def test_error_message_includes_filename(self):
        path = _write_csv("wrong_col\n1.0\n")
        try:
            with pytest.raises(ValueError) as exc_info:
                _read_csv(path)
            assert path in str(exc_info.value)
        finally:
            os.unlink(path)

    def test_error_message_includes_row_number(self):
        path = _write_csv("N_init,N_final,delta_Nstar\n20.0,5.0,0.5\nbad,5.0,0.5\n")
        try:
            with pytest.raises(ValueError, match="row 3"):
                _read_csv(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# (d) build_instanton_grid dispatcher
# ---------------------------------------------------------------------------

class TestBuildInstantonGrid:
    def setup_method(self):
        self.model_list = [{"label": "M"}]
        self.N_init_array  = _make_objs(20.0)
        self.N_final_array = _make_objs(5.0)
        self.dns_array     = _make_objs(1.0)

    def test_no_csv_delegates_to_cartesian(self):
        args = SimpleNamespace(sample_grid_csv=None)
        pool = MagicMock()
        result = build_instanton_grid(
            pool, self.model_list, args,
            self.N_init_array, self.N_final_array, self.dns_array,
        )
        expected = build_cartesian_grid(
            self.model_list, self.N_init_array, self.N_final_array, self.dns_array
        )
        assert result == expected

    def test_csv_path_delegates_to_csv(self):
        csv_content = "N_init,N_final,delta_Nstar\n20.0,5.0,1.0\n"
        path = _write_csv(csv_content)
        try:
            args = SimpleNamespace(
                sample_grid_csv=path,
                N_init_values=[],
                N_final_values=[],
                delta_Nstar_values=[],
            )
            pool = MagicMock()
            pool.object_get.side_effect = lambda cls, payload_data=None, **kw: [
                _Obj(r["value"]) for r in payload_data
            ]
            with patch("config.grid_builder.ray.get", new=lambda x: x):
                result = build_instanton_grid(pool, self.model_list, args)
            assert len(result) == len(self.model_list) * 1
        finally:
            os.unlink(path)

    def test_csv_with_conflicting_values_warns(self, capsys):
        csv_content = "N_init,N_final,delta_Nstar\n20.0,5.0,1.0\n"
        path = _write_csv(csv_content)
        try:
            args = SimpleNamespace(
                sample_grid_csv=path,
                N_init_values=[20.0, 25.0],   # non-empty — conflict
                N_final_values=[],
                delta_Nstar_values=[],
            )
            pool = MagicMock()
            pool.object_get.side_effect = lambda cls, payload_data=None, **kw: [
                _Obj(r["value"]) for r in payload_data
            ]
            with patch("config.grid_builder.ray.get", new=lambda x: x):
                build_instanton_grid(pool, self.model_list, args)
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "--N-init-values" in captured.out
        finally:
            os.unlink(path)
