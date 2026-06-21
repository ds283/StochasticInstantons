"""
Unit tests for the r_max diagnostic flags added to _classify_r_max.

Two synthetic zeta(r) profiles are exercised:
  - Profile A: both C and C_bar decay well below threshold within the computed
    grid  => r_max_C_bar_extrapolated=False, r_max_C_at_grid_edge=False
  - Profile B: both C and C_bar remain above threshold at the last computed
    sample => r_max_C_bar_extrapolated=True,  r_max_C_at_grid_edge=True
"""

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_r_max

C_THRESHOLD = 0.4
C_BAR_THRESHOLD = 0.4


class TestClassifyRMaxNoExtrapolation:
    """Profile A — both functions decay below threshold within the grid."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        # C peaks above threshold then decays; last sample well below threshold
        self.C_v = np.array([0.8, 0.6, 0.35, 0.15, 0.05])
        # C_bar similarly decays below threshold before the last sample
        self.C_bar_v = np.array([0.9, 0.7, 0.45, 0.25, 0.10])

        self.r_max_C, self.r_max_C_bar, self.r_max_C_at_grid_edge, self.r_max_C_bar_extrapolated = (
            _classify_r_max(self.r_v, self.C_v, self.C_bar_v, C_THRESHOLD, C_BAR_THRESHOLD)
        )

    def test_r_max_C_not_none(self):
        assert self.r_max_C is not None

    def test_r_max_C_correct_value(self):
        # Largest r with C >= 0.4 is r=0.2 (C=0.6); r=0.3 has C=0.35 < 0.4
        assert self.r_max_C == pytest.approx(0.2)

    def test_r_max_C_bar_not_none(self):
        assert self.r_max_C_bar is not None

    def test_r_max_C_bar_correct_value(self):
        # Largest r with C_bar >= 0.4 is r=0.3 (C_bar=0.45); r=0.4 has C_bar=0.25 < 0.4
        assert self.r_max_C_bar == pytest.approx(0.3)

    def test_r_max_C_at_grid_edge_false(self):
        assert self.r_max_C_at_grid_edge is False

    def test_r_max_C_bar_extrapolated_false(self):
        assert self.r_max_C_bar_extrapolated is False


class TestClassifyRMaxWithExtrapolation:
    """Profile B — both C and C_bar remain above threshold at the grid edge."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        # C remains above threshold at every sample, including the last
        self.C_v = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        # C_bar likewise stays above threshold through the last sample
        self.C_bar_v = np.array([0.8, 0.75, 0.65, 0.55, 0.45])

        self.r_max_C, self.r_max_C_bar, self.r_max_C_at_grid_edge, self.r_max_C_bar_extrapolated = (
            _classify_r_max(self.r_v, self.C_v, self.C_bar_v, C_THRESHOLD, C_BAR_THRESHOLD)
        )

    def test_r_max_C_not_none(self):
        assert self.r_max_C is not None

    def test_r_max_C_is_grid_edge(self):
        # Backward scan terminates immediately at i = len(r_v) - 1
        assert self.r_max_C == pytest.approx(float(self.r_v[-1]))

    def test_r_max_C_bar_not_none(self):
        assert self.r_max_C_bar is not None

    def test_r_max_C_bar_is_extrapolated(self):
        # C_bar_last=0.45 >= threshold=0.4, so extrapolation formula is used
        C_bar_last = float(self.C_bar_v[-1])
        r_last = float(self.r_v[-1])
        expected = r_last * (C_bar_last / C_BAR_THRESHOLD) ** (1.0 / 3.0)
        assert self.r_max_C_bar == pytest.approx(expected)

    def test_r_max_C_at_grid_edge_true(self):
        assert self.r_max_C_at_grid_edge is True

    def test_r_max_C_bar_extrapolated_true(self):
        assert self.r_max_C_bar_extrapolated is True


class TestClassifyRMaxNoneCase:
    """Neither C nor C_bar ever exceed threshold — both r_max values are None."""

    def setup_method(self):
        self.r_v = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        self.C_v = np.array([0.1, 0.15, 0.2, 0.15, 0.1])
        self.C_bar_v = np.array([0.05, 0.1, 0.15, 0.1, 0.05])

        self.r_max_C, self.r_max_C_bar, self.r_max_C_at_grid_edge, self.r_max_C_bar_extrapolated = (
            _classify_r_max(self.r_v, self.C_v, self.C_bar_v, C_THRESHOLD, C_BAR_THRESHOLD)
        )

    def test_r_max_C_is_none(self):
        assert self.r_max_C is None

    def test_r_max_C_bar_is_none(self):
        assert self.r_max_C_bar is None

    def test_r_max_C_at_grid_edge_false_when_r_max_C_none(self):
        assert self.r_max_C_at_grid_edge is False

    def test_r_max_C_bar_extrapolated_false_when_r_max_C_bar_none(self):
        assert self.r_max_C_bar_extrapolated is False
