"""
Unit tests for _classify_radii.

Three synthetic C(r) profiles are exercised:

  Profile A: C peaks above threshold then decays to well below it before the
    grid edge.  r_max is found in the interior; r_peak is at the first sample.
    => r_max_at_grid_edge=False, r_peak_at_grid_edge=False

  Profile B: C stays above threshold all the way to the last sample.
    r_max is at the grid edge; r_peak is at the first sample (C monotonically
    decreasing).
    => r_max_at_grid_edge=True, r_peak_at_grid_edge=False

  Profile C: C never reaches the threshold.
    r_max is None; r_peak is still found (argmax of C).
    => r_max=None, r_max_at_grid_edge=False, r_peak at interior point
"""

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_radii

C_THRESHOLD = 0.4


class TestClassifyRadiiDecaysBeforeGridEdge:
    """Profile A — C peaks above threshold then decays below it within the grid."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        # C peaks at r=0.1 (index 0) then decays; last sample well below threshold
        self.C_v = np.array([0.8, 0.6, 0.35, 0.15, 0.05])

        self.r_max, self.r_peak, self.r_max_at_grid_edge, self.r_peak_at_grid_edge = (
            _classify_radii(self.r_v, self.C_v, C_THRESHOLD)
        )

    def test_r_max_not_none(self):
        assert self.r_max is not None

    def test_r_max_correct_value(self):
        # Backward scan: last r with C >= 0.4 is r=0.2 (C=0.6); C[2]=0.35 < 0.4
        assert self.r_max == pytest.approx(0.2)

    def test_r_max_at_grid_edge_false(self):
        assert self.r_max_at_grid_edge is False

    def test_r_peak_not_none(self):
        assert self.r_peak is not None

    def test_r_peak_correct_value(self):
        # argmax of C is at index 0 (C=0.8), so r_peak = r_v[0] = 0.1
        assert self.r_peak == pytest.approx(0.1)

    def test_r_peak_at_grid_edge_false(self):
        assert self.r_peak_at_grid_edge is False


class TestClassifyRadiiAtGridEdge:
    """Profile B — C stays above threshold through the last sample."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        # C monotonically decreasing but always above threshold; max at index 0
        self.C_v = np.array([0.9, 0.8, 0.7, 0.6, 0.5])

        self.r_max, self.r_peak, self.r_max_at_grid_edge, self.r_peak_at_grid_edge = (
            _classify_radii(self.r_v, self.C_v, C_THRESHOLD)
        )

    def test_r_max_not_none(self):
        assert self.r_max is not None

    def test_r_max_is_grid_edge_value(self):
        # Backward scan terminates immediately at the last sample
        assert self.r_max == pytest.approx(float(self.r_v[-1]))

    def test_r_max_at_grid_edge_true(self):
        assert self.r_max_at_grid_edge is True

    def test_r_peak_not_none(self):
        assert self.r_peak is not None

    def test_r_peak_correct_value(self):
        # argmax at index 0 (C=0.9)
        assert self.r_peak == pytest.approx(0.1)

    def test_r_peak_at_grid_edge_false(self):
        assert self.r_peak_at_grid_edge is False


class TestClassifyRadiiNoneCase:
    """Profile C — C never reaches threshold; r_max is None, r_peak still found."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        self.C_v = np.array([0.1, 0.15, 0.2, 0.15, 0.1])

        self.r_max, self.r_peak, self.r_max_at_grid_edge, self.r_peak_at_grid_edge = (
            _classify_radii(self.r_v, self.C_v, C_THRESHOLD)
        )

    def test_r_max_is_none(self):
        assert self.r_max is None

    def test_r_max_at_grid_edge_false_when_r_max_none(self):
        assert self.r_max_at_grid_edge is False

    def test_r_peak_not_none(self):
        # r_peak always exists (argmax is well-defined)
        assert self.r_peak is not None

    def test_r_peak_correct_value(self):
        # argmax at index 2 (C=0.2)
        assert self.r_peak == pytest.approx(0.3)

    def test_r_peak_at_grid_edge_false(self):
        assert self.r_peak_at_grid_edge is False
