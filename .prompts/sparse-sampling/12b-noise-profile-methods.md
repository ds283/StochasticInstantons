# Diff — noise_profile() methods on FullInstanton and SlowRollInstanton

Small, self-contained addition.  No schema changes, no factory changes,
no CSV changes.  Two methods on FullInstanton, one on SlowRollInstanton.

---

## ComputeTargets/FullInstanton.py

Add the following two methods to the `FullInstanton` class, after the
`values` property and before `compute()`.

```python
def noise_profile(
    self,
    diffusion_model: Optional[AbstractDiffusionModel] = None,
) -> Optional[List[dict]]:
    """
    Compute the pointwise noise amplitude in units of the Hawking standard
    deviation per e-fold at each stored sample point.

    Uses the diffusion model supplied to this call, or falls back to
    self._diffusion_model if none is given.  The caller is responsible for
    ensuring the diffusion model matches the one used during the solve;
    this cannot be verified until the diffusion model is promoted to a
    first-class datastore object.

    Returns a list of dicts, one per value in self._values, each with keys:
        "N"          : float  — e-fold coordinate (instanton time)
        "sigma_phi1" : float  — noise amplitude in φ1 channel (dimensionless)
        "sigma_phi2" : Optional[float]  — noise amplitude in φ2 channel,
                       or None if D22 = 0 at this point

    Returns None if self._values is empty (object not populated, or failed).

    Physical definition
    -------------------
    For a general diffusion matrix (D11, D12, D22):

        σ_φ1 = √(2 D11) |P1| + [2 D12 / √(2 D11)] |P2|
        σ_φ2 = [2 D12 / √(2 D22)] |P1| + √(2 D22) |P2|

    Both are dimensionless.  σ_φ2 = None when D22 = 0 (e.g.
    MasslessDecoupledDiffusion).
    """
    if not self._values:
        return None

    dm = diffusion_model if diffusion_model is not None else self._diffusion_model
    traj = self._trajectory.get()
    potential = traj._potential

    result = []
    for v in self._values:
        phi1 = v.phi1
        phi2 = v.phi2
        P1   = v.P1
        P2   = v.P2

        D11, D12, D22 = dm.D_matrix(phi1, phi2, potential)

        abs_P1 = abs(P1)
        abs_P2 = abs(P2)

        if D11 > 0.0:
            sqrt_2D11 = (2.0 * D11) ** 0.5
            sigma_phi1 = sqrt_2D11 * abs_P1 + (2.0 * D12 / sqrt_2D11) * abs_P2
        else:
            sigma_phi1 = None

        if D22 > 0.0:
            sqrt_2D22 = (2.0 * D22) ** 0.5
            sigma_phi2 = (2.0 * D12 / sqrt_2D22) * abs_P1 + sqrt_2D22 * abs_P2
        else:
            sigma_phi2 = None

        result.append({
            "N":          v.N.N,
            "sigma_phi1": sigma_phi1,
            "sigma_phi2": sigma_phi2,
        })

    return result


def noise_profile_arrays(
    self,
    diffusion_model: Optional[AbstractDiffusionModel] = None,
) -> Optional[dict]:
    """
    Convenience wrapper around noise_profile() that returns numpy arrays
    rather than a list of dicts, suitable for direct use in matplotlib or
    further numerical work.

    Returns a dict with keys:
        "N"          : np.ndarray, shape (n_samples,)
        "sigma_phi1" : np.ndarray, shape (n_samples,), dtype float64
                       NaN where sigma_phi1 is None
        "sigma_phi2" : np.ndarray, shape (n_samples,), dtype float64
                       NaN where sigma_phi2 is None

    Returns None if noise_profile() returns None.
    """
    import numpy as np

    profile = self.noise_profile(diffusion_model=diffusion_model)
    if profile is None:
        return None

    N_arr     = np.array([p["N"] for p in profile], dtype=float)
    s1_arr    = np.array(
        [p["sigma_phi1"] if p["sigma_phi1"] is not None else float("nan")
         for p in profile],
        dtype=float,
    )
    s2_arr    = np.array(
        [p["sigma_phi2"] if p["sigma_phi2"] is not None else float("nan")
         for p in profile],
        dtype=float,
    )
    return {"N": N_arr, "sigma_phi1": s1_arr, "sigma_phi2": s2_arr}
```

---

## ComputeTargets/SlowRollInstanton.py

Add the following two methods to the `SlowRollInstanton` class at the same
position (after the `values` property, before `compute()`).

```python
def noise_profile(
    self,
    diffusion_model: Optional[AbstractDiffusionModel] = None,
) -> Optional[List[dict]]:
    """
    Compute the pointwise noise amplitude in units of the Hawking standard
    deviation per e-fold at each stored sample point.

    In the slow-roll approximation P2 = 0 identically, so the φ2 noise
    channel does not exist and sigma_phi2 is always None.

        σ_φ1 = √(2 D11) |P1|

    (the D12 term vanishes because P2 = 0, not because D12 = 0, so this
    remains correct for any diffusion model.)

    Returns a list of dicts, one per value in self._values, each with keys:
        "N"          : float
        "sigma_phi1" : Optional[float] — None if D11 = 0 at this point
        "sigma_phi2" : None            — φ2 channel absent in slow-roll

    Returns None if self._values is empty.
    """
    if not self._values:
        return None

    dm = diffusion_model if diffusion_model is not None else self._diffusion_model
    traj = self._trajectory.get()
    potential = traj._potential

    result = []
    for v in self._values:
        phi = v.phi
        P1  = v.P1

        D11, _D12, _D22 = dm.D_matrix(phi, 0.0, potential)

        if D11 > 0.0:
            sigma_phi1 = (2.0 * D11) ** 0.5 * abs(P1)
        else:
            sigma_phi1 = None

        result.append({
            "N":          v.N.N,
            "sigma_phi1": sigma_phi1,
            "sigma_phi2": None,
        })

    return result


def noise_profile_arrays(
    self,
    diffusion_model: Optional[AbstractDiffusionModel] = None,
) -> Optional[dict]:
    """
    Convenience wrapper returning numpy arrays.  See FullInstanton.noise_profile_arrays
    for the return format.  sigma_phi2 is always an array of NaN.
    """
    import numpy as np

    profile = self.noise_profile(diffusion_model=diffusion_model)
    if profile is None:
        return None

    N_arr  = np.array([p["N"] for p in profile], dtype=float)
    s1_arr = np.array(
        [p["sigma_phi1"] if p["sigma_phi1"] is not None else float("nan")
         for p in profile],
        dtype=float,
    )
    s2_arr = np.full_like(N_arr, float("nan"))
    return {"N": N_arr, "sigma_phi1": s1_arr, "sigma_phi2": s2_arr}
```

---

## Notes for the implementer

**Imports.**  `List` is already imported in both files.  `numpy` is imported
inside `noise_profile_arrays` to avoid a module-level import in a class that
doesn't otherwise need it; this is consistent with the existing pattern in
the Ray remote functions.

**`self._trajectory` availability.**  When an instanton is loaded from the
database with `_do_not_populate=False`, `self._trajectory` is an
`InflatonTrajectoryProxy` and `self._trajectory.get()` returns the full
`InflatonTrajectory`.  When loaded with `_do_not_populate=True` (scalar-only
mode), `self._values` is empty, so `noise_profile()` returns `None` before
reaching the trajectory call.  No guard is needed.

**Units.**  The stored φ1, φ2, P1, P2 values on `FullInstantonValue` are in
Planck units (see the factory's `_populate` method).  `dm.D_matrix` expects
field values in the same units as the potential, which is also Planck units.
No unit conversion is required.

**D11 = 0 guard.**  The per-point guard `if D11 > 0.0` (rather than the
array-level guard in the Ray remote function) is correct here because we are
evaluating point by point.  A single zero would silently produce a NaN in
the array, which is harder to diagnose than an explicit None.

---

## Acceptance criteria

1. On a loaded `FullInstanton` with populated `_values`,
   `inst.noise_profile()` returns a list of dicts with keys `N`,
   `sigma_phi1`, `sigma_phi2`, with `sigma_phi2 = None` for
   `MasslessDecoupledDiffusion`.
2. `inst.noise_profile_arrays()` returns a dict of numpy arrays of the
   correct shape, with `sigma_phi2` an array of NaN.
3. On a `FullInstanton` with `_values = []` (scalar-only load or failed
   instanton), both methods return `None`.
4. The slow-roll variants behave identically, with `sigma_phi2` always
   `None` / NaN.
5. Passing an explicit `diffusion_model` argument overrides
   `self._diffusion_model` for the computation.
