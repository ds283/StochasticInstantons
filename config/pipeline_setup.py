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

import math

import numpy as np
import ray

from config.model_list import build_model_list


def _build_grid(low, high, samples, values, label):
    if len(values) > 0:
        sample = sorted(values)
    else:
        sample = sorted(np.linspace(low, high, samples, endpoint=True).tolist())
    n = len(sample)
    if n <= 20:
        formatted = [f"{v:.5g}" for v in sample]
    else:
        formatted = (
            [f"{v:.5g}" for v in sample[:10]]
            + ["..."]
            + [f"{v:.5g}" for v in sample[-10:]]
        )
    print(
        f"   -- {label}: {n} value{'' if n == 1 else 's'} = [ {', '.join(formatted)} ]"
    )
    return sample


def build_pipeline_inputs(pool, units, args) -> dict:
    """Register and return all standard pipeline parameter objects.

    Shared by main.py, plot_InstantonSolutions.py, and any future driver
    scripts that use the same CLI/YAML configuration.

    Returns a dict with keys:
        atol          -- absolute tolerance object
        rtol          -- relative tolerance object
        phi0          -- initial field value object
        pi0           -- initial field velocity object
        N_init_array  -- list of N_init objects
        N_final_array -- list of N_final objects
        dns_array     -- list of delta_Nstar objects
        model_list    -- list of {"label": str, "potential": obj} dicts
    """
    # Build sample grids (sequential: each prints its own summary line)
    N_init_sample = _build_grid(
        args.N_init_low, args.N_init_high, args.N_init_samples,
        args.N_init_values, "N_init",
    )
    N_final_sample = _build_grid(
        args.N_final_low, args.N_final_high, args.N_final_samples,
        args.N_final_values, "N_final",
    )
    dns_sample = _build_grid(
        args.delta_Nstar_low, args.delta_Nstar_high, args.delta_Nstar_samples,
        args.delta_Nstar_values, "delta_Nstar",
    )

    # Register all parameter objects in parallel
    (
        atol, rtol, phi0, pi0,
        N_init_array, N_final_array, dns_array,
    ) = ray.get([
        pool.object_get("tolerance", log10_tol=int(round(math.log10(args.abs_tol)))),
        pool.object_get("tolerance", log10_tol=int(round(math.log10(args.rel_tol)))),
        pool.object_get("phi_value", value=args.phi0_Mp * units.PlanckMass, units=units),
        pool.object_get("pi_value", value=args.pi0_Mp * units.PlanckMass, units=units),
        pool.object_get("N_init",      payload_data=[{"value": v} for v in N_init_sample]),
        pool.object_get("N_final",     payload_data=[{"value": v} for v in N_final_sample]),
        pool.object_get("delta_Nstar", payload_data=[{"value": v} for v in dns_sample]),
    ])

    model_list = build_model_list(pool, units, args)

    return {
        "atol":          atol,
        "rtol":          rtol,
        "phi0":          phi0,
        "pi0":           pi0,
        "N_init_array":  N_init_array,
        "N_final_array": N_final_array,
        "dns_array":     dns_array,
        "model_list":    model_list,
    }
