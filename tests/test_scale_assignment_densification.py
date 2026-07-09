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
Acceptance test for prompt U2a
(.prompts/gradient-coupled-plotting/02-U2a-onion-profile-cbar-and-densified-classification.md):

  (a) assign_scales(...)["C_bar"] is present, finite, and the same
      length/ordering as ["C"].
  (b) the returned r_max/r_peak numerically *differ* from what the
      pre-U2a algorithm (classify_radii fed the raw, un-densified node-level
      (r_phys, C) pair) would have produced for the same fixture.

Point (b) is deliberately an inequality check, not the usual golden-run
equality: U2a's whole point is to change what r_max/r_peak mean (they are
now classified on a densified log-r grid rather than the raw
n_collocation_points-sized node set -- see the DESIGN-DECISION comment in
scale_assignment.py's assign_scales and design doc section 7.2 "One fidelity
note"). A future reader diffing this test's assertions against a "regression"
should read this docstring first: the changed r_max/r_peak values are the
intended outcome of U2a, not a bug.
"""

import types

import numpy as np

from ComputeTargets.compaction_scalars import classify_radii
from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales
from Numerics.LGLCollocation import LGLCollocationGrid
from Units.Planck_units import Planck_units


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used
    throughout this prompt sequence (test_picard.py, test_scale_assignment.py,
    etc).
    """

    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi ** 2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi ** 2


def _make_cosmo():
    """Minimal duck-typed cosmology stand-in -- only T_CMB_Kelvin is read by
    ln_k_phys_Mpc."""
    return types.SimpleNamespace(T_CMB_Kelvin=2.725)


class _StaticTrajectory:
    """Minimal duck-typed trajectory stub with a constant (phi, pi)
    everywhere and an arbitrary N_end -- reused verbatim from
    test_scale_assignment.py, since only assign_scales' r_ratio/C/C_bar
    wiring is under test here, not the physical realism of the Leach-Liddle
    anchor value."""

    def __init__(self, phi: float, pi: float, N_end: float):
        self._phi = phi
        self._pi = pi
        self._N_end = N_end

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return self._phi

    def pi_at(self, N: float) -> float:
        return self._pi


def _fixture_result():
    """Shared fixture. Unlike test_scale_assignment.py's own low-degree
    polynomial zeta(y) (whose C(y) peaks exactly at the grid edge, where
    densification cannot move the resolved r_peak -- both the raw node grid
    and the dense grid share the same endpoint), this fixture uses a
    Gaussian bump in zeta(y) so that C(y) has a genuine *interior* maximum.
    That interior peak is where node-count resolution actually matters: the
    raw n_collocation_points-sized node grid and the densify_zeta_profile
    grid (>= 500 points) locate the interior maximum at measurably different
    r, which is exactly the n_collocation_points-dependence artifact U2a is
    meant to remove (see design doc section 7.2 and the DESIGN-DECISION
    comment in scale_assignment.py)."""
    grid = LGLCollocationGrid(9)  # n_max=8
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()
    trajectory = _StaticTrajectory(phi=10.0, pi=-0.01, N_end=100.0)

    y = grid.nodes
    zeta = 0.08 * np.exp(-((y - 0.3) ** 2) / (2.0 * 0.25 ** 2)) + 0.005 * y
    delta_s_N_final = 4.2
    C_threshold = 0.4

    result = assign_scales(
        zeta, delta_s_N_final, grid, trajectory,
        5.0, 50.0, 0.05, potential, units, cosmo, C_threshold=C_threshold,
    )
    return result, zeta, C_threshold


def test_C_bar_present_finite_and_matches_C_shape():
    """(a) C_bar is present, finite, and the same length/ordering as C."""
    result, _, _ = _fixture_result()

    assert result["failure"] is False
    assert "C_bar" in result
    C_bar = np.asarray(result["C_bar"])
    C = np.asarray(result["C"])

    assert C_bar.shape == C.shape
    assert np.all(np.isfinite(C_bar))

    # Same node ordering: C_bar must line up node-for-node with r_ratio/C/
    # r_phys, all of which are returned in original (un-sorted) grid order.
    assert C_bar.shape == np.asarray(result["r_ratio"]).shape
    assert C_bar.shape == np.asarray(result["r_phys"]).shape


def test_r_max_r_peak_differ_from_pre_U2a_raw_node_classification():
    """(b) r_max/r_peak from the new, densified-grid classification must
    numerically differ from what classify_radii would have produced when fed
    the raw, un-densified node-level (r_phys, C) pair directly -- the
    pre-U2a behaviour (see this module's own docstring for why this is a
    deliberate inequality check, not a regression)."""
    result, zeta, C_threshold = _fixture_result()

    r_phys = np.asarray(result["r_phys"])
    C = np.asarray(result["C"])
    sort_idx = np.argsort(r_phys)

    pre_U2a_r_max, pre_U2a_r_peak, _, _ = classify_radii(
        r_phys[sort_idx], C[sort_idx], C_threshold
    )

    assert result["r_max"] != pre_U2a_r_max or result["r_peak"] != pre_U2a_r_peak
