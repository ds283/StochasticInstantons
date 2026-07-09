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
CLI-level coverage for the `spectrum` subcommand of the
tools/diagnostics/GradientCoupledInstanton package. The underlying spectral
functions are already covered at the library level (test_stiffness_spectrum.py
and friends); this file only exercises `spectrum.main()`'s own argument
parsing and CSV-writing glue, which nothing else tests. Uses the smallest
possible sweep grid (one n_max/alpha/N point each) so it stays fast.
"""

import csv

from tools.diagnostics.GradientCoupledInstanton.spectrum import (
    ADJOINT_CSV_FIELDNAMES,
    CSV_FIELDNAMES,
    main,
)


def test_spectrum_mode_writes_csv(tmp_path):
    output = tmp_path / "spectrum.csv"
    rc = main(["--n-max", "8", "--alpha", "0.05", "--N", "1.0", "--output", str(output)])
    assert rc == 0
    assert output.exists()

    with open(output, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert set(rows[0]) == set(CSV_FIELDNAMES)


def test_adjoint_mode_writes_csv(tmp_path):
    output = tmp_path / "adjoint.csv"
    rc = main(["--n-max", "8", "--alpha", "0.05", "--N", "1.0", "--mode", "adjoint", "--output", str(output)])
    assert rc == 0
    assert output.exists()

    with open(output, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert set(rows[0]) == set(ADJOINT_CSV_FIELDNAMES)
