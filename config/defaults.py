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

DEFAULT_STRING_LENGTH = 256

DEFAULT_FLOAT_PRECISION = 1e-7

DEFAULT_REDSHIFT_PRECISION = 1e-7
DEFAULT_REDSHIFT_RELATIVE_PRECISION = 1e-7

DEFAULT_DIMENSIONLESS_QUANTITY_PRECISION = 1e-7
DEFAULT_DIMENSIONLESS_QUANTITY_RELATIVE_PRECISION = 1e-5

DEFAULT_DIMENSIONFUL_QUANTITY_PRECISION = 1e-7
DEFAULT_DIMENSIONFUL_QUANTITY_RELATIVE_PRECISION = 1e-5

DEFAULT_EFOLD_PRECISION = 1e-8
DEFAULT_EFOLD_RELATIVE_PRECISION = 1e-8

DEFAULT_ABS_TOLERANCE = 1e-8
DEFAULT_REL_TOLERANCE = 1e-8

DEFAULT_ALPHA_PRECISION = 1e-8
DEFAULT_ALPHA_RELATIVE_PRECISION = 1e-8

# LGL collocation point count for the onion model (GradientCoupledInstanton).
# 17 points <=> polynomial degree n_max = 16. This is a starting point for the
# mandatory n_max convergence scan (onion_model_planning.md), not a value to
# be trusted as final without that scan.
DEFAULT_N_COLLOCATION_POINTS = 17
