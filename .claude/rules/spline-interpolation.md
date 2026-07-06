# Spline interpolation discipline

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies everywhere a spline or interpolating function is
constructed — `ComputeTargets/`, `Datastore/`, plot scripts, or any new file.

## Core rules

**1. All splines must use `SplineWrapper`.**  
Never call `scipy.interpolate.make_interp_spline`, `CubicSpline`, `interp1d`,
or any other interpolation primitive directly. Import and use
`Interpolation.spline_wrapper.SplineWrapper` instead. This ensures coordinate
transforms are applied consistently and the root-finding API is always available.

```python
from Interpolation.spline_wrapper import SplineWrapper

spline = SplineWrapper(x, y, x_transform='linear', y_transform='sinh', k=3)
value  = spline(x_query)
```

**2. When implementing a new spline, ask the human which transforms to apply.**  
Do not choose transforms silently. Splines over an exponentially large dynamic
range in x or y produce poor interpolation; the human must decide whether the
quantity needs a `log` or `sinh` transform. Present the independent variable,
the dependent variable, and your assessment of the dynamic range, then wait
for a decision before writing the code.

**3. When implementing a root-finder that goes through a spline, ask the human
how to handle it, or use the transformed-coordinate root-finding pattern.**  
Root-finding directly on the inverse-transformed output can be poorly
conditioned when the y-transform is `sinh` or `log`. The preferred approach
works entirely in transformed space:

```python
c_t   = wrapper.transform_y(c)
lo_t  = wrapper.transform_x(x_lo)
hi_t  = wrapper.transform_x(x_hi)
root_t = brentq(lambda x_t: wrapper.raw(x_t) - c_t, lo_t, hi_t)
x_root = wrapper.invert_x(root_t)
```

If uncertain whether this pattern applies, ask the human before writing the
root-finder.

---

## Transform reference

| Transform | Forward          | Inverse   | Use when                                      |
|-----------|------------------|-----------|-----------------------------------------------|
| `linear`  | identity         | identity  | modest range, no special structure            |
| `log`     | `log(x)`         | `exp`     | strictly positive, spans orders of magnitude  |
| `sinh`    | `arcsinh(x)`     | `sinh`    | either sign, spans orders of magnitude        |

---

## Existing splines — transform catalogue

| File | Spline | x_transform | y_transform | Rationale |
|------|--------|-------------|-------------|-----------|
| `ComputeTargets/InflatonTrajectory.py` | `_phi_spline` | `linear` | `linear` | φ varies O(10×); safe |
| `ComputeTargets/InflatonTrajectory.py` | `_pi_spline` | `linear` | `sinh` | π can be either sign; 10²–10³ range |
| `ComputeTargets/FullInstanton.py` | `phi1_sp`, `phi2_sp` (Picard) | `linear` | `linear` | modest range |
| `ComputeTargets/FullInstanton.py` | `P1_sp`, `P2_sp` (Picard) | `linear` | `sinh` | exponentially growing backward ODE mode; either sign |
| `ComputeTargets/FullInstanton.py` | output `interp_phi` | `linear` | `linear` | same as phi above |
| `ComputeTargets/FullInstanton.py` | output `interp_P` | `linear` | `sinh` | same as P above |
| `ComputeTargets/SlowRollInstanton.py` | `phi_sp` | `linear` | `linear` | modest range |
| `ComputeTargets/SlowRollInstanton.py` | `P1_sp` | `linear` | `sinh` | same growing-mode argument as FullInstanton P₁ |
| `ComputeTargets/CompactionFunction.py` | `zeta_spline` | `log` | `linear` | r = 2π/k spans exp(N_total) ≈ 10²⁶; ζ is O(1) |
| `ComputeTargets/CompactionFunction.py` | `cumulative_at_r` | `log` | `linear` | same log-r motivation |
| `ComputeTargets/GradientCoupledInstanton/picard.py` | `phi_splines`, `pi_splines` | `linear` | `linear` | modest range, matches FullInstanton's phi1/phi2 |
| `ComputeTargets/GradientCoupledInstanton/picard.py` | `rfield_splines`, `rmom_splines` | `linear` | `sinh` | response fields, same growing-mode argument as FullInstanton P₁/P₂ |
| `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py` | onto-`N_sample` interpolation of `phi`/`pi` (reuses `picard._build_node_splines`) | `linear` | `linear` | same as picard.py's own phi/pi splines above |
| `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py` | onto-`N_sample` interpolation of `rfield`/`rmom` (reuses `picard._build_node_splines`) | `linear` | `sinh` | same as picard.py's own rfield/rmom splines above |
| `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py` | `zeta_C_r_at_time`'s per-node phi/pi reconstruction splines | `linear` | `linear` | same rationale as picard.py's own phi/pi splines; built over the (typically short) stored `N_sample` grid rather than the dense solver grid |

---

## `derivative()` and the chain rule

`SplineWrapper.derivative()` returns a `_SplineDerivativeWrapper` that applies
the full chain rule and returns dy/dx in **original coordinates**. Callers do
not need to handle the chain rule themselves:

```python
zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)
zeta_prime  = zeta_spline.derivative()   # returns dζ/dr (not dζ/d(log r))
dz_dr = zeta_prime(r)                    # correct dζ/dr in original coords
```

Do not apply a manual `1/r` correction at the call site — it is already inside
the derivative wrapper.

---

## What is forbidden

```python
# NEVER — bypasses transforms and root-finding API
from scipy.interpolate import make_interp_spline, CubicSpline, interp1d
spline = make_interp_spline(x, y)

# NEVER — root-finding directly on the untransformed output when y_transform
# is 'sinh' or 'log' (poorly conditioned)
brentq(lambda x: spline(x) - target, lo, hi)

# NEVER — applying the chain-rule correction manually at the call site
dz_dr = spline.derivative()(np.log(r)) / r   # SplineWrapper.derivative() does this
```
