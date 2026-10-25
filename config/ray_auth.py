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

import os
import sys

# Ray's token authentication, named rather than left to Ray's default (ray-sqla-align; the token
# half of SecondaryGWKit's config/ray_local.py). Since Ray 2.59, when RAY_AUTH_MODE is unset, the
# mode depends on how Ray is started: a new local instance (ray.init(address="local")) runs in
# token mode and logs a warning saying so; `ray start --head`, as ray_cluster.sh runs it, does the
# same whenever the token file exists; but a driver attaching to an explicit host:port never does.
# So SI's cluster came up in token mode and refused main.py's attach with AuthenticationError
# (ray-sqla-align 01, V0). With the mode named, every route runs in token mode, a driver sends the
# token, and Ray logs nothing.
#
# Every Ray start imports this module before its ray.init: main.py, both plot scripts and
# tests/conftest.py (whose subprocesses inherit the variable); tests/test_ray_auth.py checks that
# they do. ray_cluster.sh names the mode for the cluster itself. A value already in the environment
# (for instance `disabled`) is left as it is.
#
# Ray reads the mode into its config once, when `ray` is imported, and the drivers (and
# RunDrivers/registered_run.py, which runs main.py in-process) import `ray` first. Without a
# refresh the driver keeps `disabled` while the processes it starts inherit `token`, and every start
# is refused: SecondaryGWKit's issue
# [02-the-token-mode-setting-comes-after-import-ray-so-every-ray-start-fails].
# Config.initialize("") is the refresh Ray's own _enable_token_auth makes.
#
# The token is ~/.ray/auth_token, shared by every project of this user on the machine; keep it at
# mode 600, and never print or copy it.
RAY_AUTH_MODE = "token"
if "RAY_AUTH_MODE" not in os.environ:
    os.environ["RAY_AUTH_MODE"] = RAY_AUTH_MODE
    if "ray._raylet" in sys.modules:
        sys.modules["ray._raylet"].Config.initialize("")
