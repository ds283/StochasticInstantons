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

import csv
import itertools

import ray


def _read_csv(csv_path: str) -> list:
    """
    Parse a sample-grid CSV file.

    Required columns (any order, case-sensitive): N_init, N_final, delta_Nstar.
    Raises ValueError for: missing column, non-numeric value, or empty file.
    Returns a list of dicts with float values.
    """
    try:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(line for line in f if not line.startswith("#"))
            if reader.fieldnames is None:
                raise ValueError(f"'{csv_path}': file is empty")
            required = {"N_init", "N_final", "delta_Nstar"}
            missing = required - set(reader.fieldnames)
            if missing:
                raise ValueError(
                    f"'{csv_path}': missing required column(s): "
                    f"{', '.join(sorted(missing))}"
                )
            rows = []
            for lineno, row in enumerate(reader, start=2):
                try:
                    rows.append(
                        {
                            "N_init": float(row["N_init"]),
                            "N_final": float(row["N_final"]),
                            "delta_Nstar": float(row["delta_Nstar"]),
                        }
                    )
                except (ValueError, TypeError) as exc:
                    raise ValueError(
                        f"'{csv_path}': row {lineno}: non-numeric value — {exc}"
                    ) from exc
    except OSError as exc:
        raise ValueError(f"Cannot open CSV file '{csv_path}': {exc}") from exc
    if not rows:
        raise ValueError(f"'{csv_path}': file contains no data rows")
    return rows


def build_cartesian_grid(model_list, N_init_array, N_final_array, delta_Nstar_array) -> list:
    """
    Build the full (model_idx, N_init, N_final, delta_Nstar) Cartesian product.
    Extracted verbatim from the inline itertools.product call in main.py.
    """
    return list(
        itertools.product(
            range(len(model_list)), N_init_array, N_final_array, delta_Nstar_array
        )
    )


def build_grid_from_csv(pool, csv_path: str, model_list) -> list:
    """
    Parse csv_path (columns: N_init, N_final, delta_Nstar — float values),
    mint/look up the corresponding domain objects via pool.object_get using the
    same payload_data=[{"value": v}] pattern as build_pipeline_inputs, and
    return (model_idx, N_init, N_final, delta_Nstar) tuples crossed against
    model_list only — CSV rows are NOT crossed against each other.

    Duplicate triples in the CSV are harmless: identical float values resolve
    to the same store_id, so no duplicate database rows are created.
    """
    rows = _read_csv(csv_path)
    n_rows = len(rows)
    print(f"   -- sample-grid-csv: {n_rows} sample point(s) from '{csv_path}'")
    for col in ("N_init", "N_final", "delta_Nstar"):
        vals = sorted({r[col] for r in rows})
        n_u = len(vals)
        if n_u == 1:
            print(f"      {col}: {vals[0]:.5g} (1 unique value)")
        else:
            print(f"      {col}: {vals[0]:.5g} .. {vals[-1]:.5g} ({n_u} unique values)")

    N_init_objects, N_final_objects, dns_objects = ray.get(
        [
            pool.object_get(
                "N_init", payload_data=[{"value": r["N_init"]} for r in rows]
            ),
            pool.object_get(
                "N_final", payload_data=[{"value": r["N_final"]} for r in rows]
            ),
            pool.object_get(
                "delta_Nstar",
                payload_data=[{"value": r["delta_Nstar"]} for r in rows],
            ),
        ]
    )

    return [
        (model_idx, N_init_obj, N_final_obj, dns_obj)
        for model_idx in range(len(model_list))
        for N_init_obj, N_final_obj, dns_obj in zip(
            N_init_objects, N_final_objects, dns_objects
        )
    ]


def build_instanton_grid(
    pool,
    model_list,
    args,
    N_init_array=None,
    N_final_array=None,
    delta_Nstar_array=None,
) -> list:
    """
    Top-level dispatcher for instanton grid construction.

    When args.sample_grid_csv is set: parse the CSV file and delegate to
    build_grid_from_csv.  The axis-grid arguments (--N-init-*, --N-final-*,
    --delta-Nstar-*) are superseded by the CSV; a warning is printed when the
    explicit *-values lists are non-empty, since that combination is almost
    certainly unintentional.  The low/high/samples variants are silently
    ignored when --sample-grid-csv is given — to error in those cases as well,
    compare args.*_low/high/samples against the parser defaults explicitly
    before calling this function.

    When args.sample_grid_csv is None: delegate to build_cartesian_grid with
    the supplied N_init_array, N_final_array, delta_Nstar_array arrays.
    """
    if getattr(args, "sample_grid_csv", None):
        conflict = []
        if getattr(args, "N_init_values", []):
            conflict.append("--N-init-values")
        if getattr(args, "N_final_values", []):
            conflict.append("--N-final-values")
        if getattr(args, "delta_Nstar_values", []):
            conflict.append("--delta-Nstar-values")
        if conflict:
            print(
                f"WARNING: --sample-grid-csv is set; the following axis-grid "
                f"argument(s) will be ignored: {', '.join(conflict)}"
            )
        return build_grid_from_csv(pool, args.sample_grid_csv, model_list)

    return build_cartesian_grid(model_list, N_init_array, N_final_array, delta_Nstar_array)
