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

class SQLAFactoryBase:
    def register(self):
        raise NotImplementedError

    def build(self, payload, conn, table, inserter, tables, inserters):
        raise NotImplementedError

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError

    def validate_on_startup(self, conn, table, tables, prune=False):
        raise NotImplementedError
