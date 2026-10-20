# 04 — adopt `raypoolkit`

**Subject:** Replace SI's copy of `RayWorkPool` with the packaged `raypoolkit.RayWorkPool`
**Commit:** `ef13445`, on branch `dk-and-rpk-migration`, on top of `9a7cb50`
**Date:** 2026-10-20, by Claude Sonnet 5.5
**Result:** **COMPLETE.** W1–W5 hold, and **RayPoolKit G4 holds** (checklist item 8, items 1–5).
`RayTools/` is gone; the three drivers import `RayWorkPool` from `raypoolkit`; `_default_store_handler`
is dropped. RayPoolKit's script at a throwaway commit of the staged tree reports 0 imports, 0 private
names, 0 `import_module` calls, 16 calls, `constructs` 16. The suites give 680 (679 passed, 1 skipped)
and 61 (60 passed, 1 skipped), as at 03. No Ray was started and no driver ran by the agent; no store
was opened. One issue is opened, for 12.

Prompt: [`.prompts/dk-and-rpk-migration/04-adopt-raypoolkit.md`](../../.prompts/dk-and-rpk-migration/04-adopt-raypoolkit.md),
corrected by the orchestrator's brief (nine corrections; below). Scratch outputs were kept outside
both repositories.

## What shipped

- **W1.** `git rm RayTools/RayWorkPool.py RayTools/__init__.py`. The ignored `RayTools/__pycache__/`
  (two `.pyc` files, 2026-06-16) survived the `git rm` and kept the directory; it was removed with
  `rm -r`, and then the empty `RayTools/` with `rmdir`. `ls -d RayTools` now fails and
  `git ls-files RayTools` is empty.
- **W2.** `main.py:45`, `plot_GradientCoupledSolutions.py:100`, `plot_InstantonSolutions.py:72`
  are `from raypoolkit import RayWorkPool` (a one-line replacement each, in place; the file's
  import order is not touched).
- **W3.** In `main.py`, seven changed lines: `:45` as above (loses `_default_store_handler`); and six
  deleted, at their `0c3d4b6` lines: `store_handler,` (`:412`, `_run_instanton_queue`'s parameter),
  `store_handler=store_handler,` (`:499`), `store_handler=_default_store_handler,` at `:666`
  (STAGE G), `:826` (STAGE 2), `:850` (STAGE 3) and `:1099` (the construction at `:1094`). The two
  other compute sites (`:385`, `:720`) keep `pipeline_store_handler` and
  `inflaton_trajectory_store_handler`. The other arguments of these calls are untouched, in place.
- **W4.** No other pool site changed. The plot scripts' diff is the one import line each.
- **W5.** The prose the commit made false:
  - `CLAUDE.md:101` is now `Datastore/SQL/ShardedPool.py` alone (the list's single-entry form).
  - `.claude/rules/ray-dispatch.md:99-112`, "Why `RayWorkPool` requires plain classes": it names
    `raypoolkit.RayWorkPool`, pinned in `requirements.txt` and not a file of this repository, and
    cites the same three behaviours at the package's lines at `v0.2.0`: `if obj.available:` at
    `:385`; the compute handler at `:424-426` (default `obj.compute(**kwargs)`, `:75-76`), which
    must return an `ObjectRef`, never `.remote()`-called by the pool; and the store handler at `:471`
    (default `obj.store()`, `:79-80`), the persist handler following at `:481`. I read all of these
    with `git -C RayPoolKit show v0.2.0:raypoolkit/RayWorkPool.py`. The rule's argument is unchanged.
  - `.documents/FILE_MAP.md:31`: the row now has `— (not a file of this repository)` and
    `raypoolkit.RayWorkPool`, and says the class is from the `raypoolkit` package pinned in
    `requirements.txt`; its description of the state machine stays. `:287`: the row
    `RayTools/ (other files)` is deleted (it described a directory that is gone and never held another
    file).
  - `.documents/INFRASTRUCTURE.md:353` and `.documents/architecture-summary.md:321`: the opening
    sentence names `RayWorkPool` "from the `raypoolkit` package (pinned in `requirements.txt`)".
  - `.documents/architecture-summary.md:27-28`: the layout's `RayTools/` / `  RayWorkPool.py` become
    `(raypoolkit package, pinned in requirements.txt)` / `  RayWorkPool`.
  - Nothing else in those files changed.
- **The records:** the board's §1 row, items W1–W5, the RayPoolKit G4 row, §3's new issue, and
  `### 5.16 After prompt 04 (2026-10-20)`; `.documents/OPEN-ISSUES.md` §6a (60 to 61 open).
  `.prompts/INDEX.md` is the orchestrator's and is not touched.

The drivers' diff, in full (`git diff HEAD -U0 -- main.py plot_GradientCoupledSolutions.py plot_InstantonSolutions.py`, index lines omitted):

```diff
diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -45 +45 @@ from MetadataConcepts import store_tag, tolerance
-from RayTools.RayWorkPool import RayWorkPool, _default_store_handler
+from raypoolkit import RayWorkPool
@@ -412 +411,0 @@ def _run_instanton_queue(
-    store_handler,
@@ -499 +497,0 @@ def _run_instanton_queue(
-        store_handler=store_handler,
@@ -666 +663,0 @@ def _run_gradient_branch(
-        store_handler=_default_store_handler,
@@ -826 +822,0 @@ def run_all_pipelines(
-            store_handler=_default_store_handler,
@@ -850 +845,0 @@ def run_all_pipelines(
-            store_handler=_default_store_handler,
@@ -1099 +1093,0 @@ def run_all_pipelines(
-                store_handler=_default_store_handler,
diff --git a/plot_GradientCoupledSolutions.py b/plot_GradientCoupledSolutions.py
--- a/plot_GradientCoupledSolutions.py
+++ b/plot_GradientCoupledSolutions.py
@@ -100 +100 @@ from plotting.sampling import _evenly_sample, _safe_name, _safe_num
-from RayTools.RayWorkPool import RayWorkPool
+from raypoolkit import RayWorkPool
diff --git a/plot_InstantonSolutions.py b/plot_InstantonSolutions.py
--- a/plot_InstantonSolutions.py
+++ b/plot_InstantonSolutions.py
@@ -72 +72 @@ from plotting.sampling import _evenly_sample, _safe_name, _safe_num
-from RayTools.RayWorkPool import RayWorkPool
+from raypoolkit import RayWorkPool
```

## Deviations from the prompt

1. **The board section is `### 5.16`, not `### 5.8`** (§5.8 is taken; the board ran to §5.15).
   `STRUCTURALLY REQUIRED` (the orchestrator's correction 1).
2. **Line numbers** are those at `0c3d4b6`, not `7bb3efd`'s (the prompt's `:408` for the parameter was
   `:410` at `7bb3efd` and is `:412` now). `STRUCTURALLY REQUIRED` (correction 2).
3. **The re-measure finds 2 string literals and 1 test module naming `RayTools`**, where §2.1 and
   acceptance 3 expect 0. They are the module docstrings 01 added (`stage_counts.py:16`,
   `tests/test_rehearsal_stage_counts.py:16`, and the test's `:22`). Neither is edited
   (`stage_counts.py` is frozen until 07; the test by README §5 rule 7), so acceptance 3 reads
   "2 string literals, both these docstrings, unchanged by 04", and §2.3.6 reads "no test imports or
   constructs `RayTools` or `RayWorkPool`". `STRUCTURALLY REQUIRED` (correction 3).
4. **§2.1.2's `git grep` finds two more lines** than the prompt lists:
   `ComputeTargets/GradientCoupledInstanton/picard.py:452` and
   `tests/test_rehearsal_stage_counts.py:22`. Neither is edited. `STRUCTURALLY REQUIRED` (correction 4);
   the `picard.py` comment is opened as an issue (below).
5. **One issue is opened** (correction 6), `[pool-prose-stale-after-raypoolkit-adoption]`, owner 12,
   with `.documents/OPEN-ISSUES.md` in the same commit; that file is outside the prompt's §5 list.
   `STRUCTURALLY REQUIRED` (README §5 rules 3 and 4; `CLAUDE.md`'s maintenance rule).
6. **Breakage 3 is not reported by the script** (it reports 0 imports and 0 private names, since
   `raypoolkit.RayWorkPool` is not a `RayTools` module). Its catch is the import-check script's
   private-name count, and `git grep`. `STRUCTURALLY REQUIRED` (correction 7).
7. **The suites' commands** are `-p no:cacheprovider`, and `RAY_ADDRESS=local` for the integration
   run. `IMPLEMENTATION CHOICE` (README §5 rules 16–17; correction 8).
8. **`FILE_MAP.md:287`: the row is deleted** rather than reworded. `IMPLEMENTATION CHOICE` (both
   offered by the brief).
9. **The `architecture-summary.md:27` layout line** reads `(raypoolkit package, pinned in
   requirements.txt)`, in place of `RayTools/`, so that the tree's shape is kept and nothing is
   dropped from it. `IMPLEMENTATION CHOICE`.
10. **The import line is replaced in place** and the three files' import blocks are not re-sorted
    (`from raypoolkit import …` now sits between `MetadataConcepts` and `Units`, not in the
    case-folded position `ruff`'s isort rule might give it). README §5 rule 15 (no reformatting).
    `IMPLEMENTATION CHOICE`.
11. **`sed -i -e …` on macOS** (BSD `sed`) treated `-e` as the backup suffix and left `main.py-e`
    beside `main.py` after the first edit; I noticed it in `git status`, deleted it, and the rest used
    `sed -i ''`. Nothing of it is in the commit. `IMPLEMENTATION CHOICE` (a slip, corrected before any
    staging).
12. The import-check script counts a `from X import Y` whose `Y` is a submodule as resolved, and
    treats a namespace package (no `__init__`, no module file) as unresolved (the brief's warning
    about the surviving `RayTools/__pycache__/`). `IMPLEMENTATION CHOICE`.
13. None is `UNINTENDED DRIFT`.

## Verification performed

### Before

- `git log` at the start: `HEAD` `9a7cb50`, clean; RayPoolKit `HEAD` `17029d9`, working tree clean.
- No Ray process (`pgrep` finds none), `RAY_ADDRESS` unset. Load at the start 17 / 27 / 31 (1/5/15
  min), 10 CPUs.

### §2.1.1 — the re-measure, at `9a7cb50` (SI's `HEAD`)

`./venv/bin/python docs/adoption/measure_client_pools.py si --commit 9a7cb5013be0a85cec4713403519d7140719e4a0`,
from RayPoolKit's root with its own venv, exit 0, saved. Header `Verdicts by: raypoolkit 0.2.0`.
**3 imports** (module level; 1 naming `_default_store_handler`), **2 string literals**, **0
`import_module` calls**, **16 calls**, `constructs` 16, **5 flags on 4 calls**. 12 calls have no
compute handler and 4 have one; 11 use `store_results=True`.

Its difference from the `7bb3efd` appendix (`measure/out/7bb3efd-raypoolkit-measure_client_pools.md`),
each line explained:

| Line | `7bb3efd` | `9a7cb50` | Why |
|---|---|---|---|
| header: commit | `7bb3efd` | `9a7cb50` | the tree measured |
| `Files:` tracked; `.py` parsed | 363; 193 | 421; 199 | 01's tooling, tests and records; the campaign's prompts and results notes |
| string literals naming `RayTools` | 0 | 2 | the docstrings 01 added (`84a5cfc`); deviation 3 |
| test modules naming `RayTools` or `RayWorkPool` | 0 | 1 | `tests/test_rehearsal_stage_counts.py:22`; deviation 3 |
| non-`.py` lines naming either | 89 | 292 | `.prompts/` 27 to 219 (183 at `0c3d4b6`; the orchestrator's note for 04 in `9a7cb50` adds 36; the rest is this campaign's records), `.documents/` 44 to 55 (01's, 03's results notes and `verification.md`), `.claude/` 17 and `CLAUDE.md` 1 unchanged in count (`CLAUDE.md:95` to `:101`) |
| every call's line | e.g. `main.py:221`, `:1092`; `plot_*:938`, `:1171` | `:223`, `:1094`; `:939`, `:1172` | `main.py` by +2 and the plot scripts by +1: 01's provenance import and print |
| the 5 flags' keyword lines | `:396`, `:505`, `:729-730`, `:1107` | `:398`, `:507`, `:731-732`, `:1109` | the same shift |
| the handler-spelling table | one row of compute sites with `_default_store_handler` | the same rows, lines shifted | none |

Every other cell is unchanged: the verdicts, the sizes, the handler spellings and the `title` and
`results` columns.

### §2.1.2 — `git grep`

`git grep -n -e RayTools -e _default_store_handler -- ':!.prompts' ':!.documents' ':!.claude' ':!CLAUDE.md'`
(before the change) gives 11 lines: `RayTools/RayWorkPool.py:79`, `:94`; the three imports; the four uses
(`main.py:666`, `:826`, `:850`, `:1099`); `picard.py:452`; `tests/test_rehearsal_stage_counts.py:22`.
After the change it gives 2: those last two. (`git grep` of `main.py` for `_default_store_handler`
gives nothing.)

### §2.3.1 — RayPoolKit's script at a throwaway commit of the staged tree

The script reads git, not the working tree, so it was run at a commit. The throwaway commit
`db29b7ffa061e60788ebe3975ec4b45f28daed1d` was built without a branch and without touching the
real index or working tree: the real index's path read first (`REAL=$(git rev-parse --git-path
index)`), copied to the scratchpad, `GIT_INDEX_FILE` pointed at the copy, `git write-tree` and
`git commit-tree <tree> -p HEAD`, then `unset GIT_INDEX_FILE`. The tree was the staged change: the
two deletions, the three drivers and the five prose files (the board, the issue index and this note
were not yet written, so the commit differs from the real one in those and in nothing else).
`git branch --contains` of it lists no branch. Nothing was checked out, switched, stashed or reset.

`./venv/bin/python docs/adoption/measure_client_pools.py si --commit db29b7ffa061e60788ebe3975ec4b45f28daed1d`,
exit 0, saved; header `Verdicts by: raypoolkit 0.2.0`; `Files: 419 tracked`, `199 .py files outside
RayTools/ parsed`.

| Measure | `7bb3efd` | `9a7cb50` (before) | Throwaway commit |
|---|---|---|---|
| `RayTools/` table | 2 files | 2 files | **empty** |
| Imports of a `RayTools` module | 3 | 3 | **0** |
| … naming a private name | 1 | 1 | **0** |
| String literals naming `RayTools` | 0 | 2 | **2** (the two docstrings, unchanged) |
| `import_module` / `__import__` calls | 0 | 0 | **0** |
| `RayWorkPool(...)` calls | 16 | 16 | **16** |
| … no compute handler / compute handler given | 12 / 4 | 12 / 4 | 12 / 4 |
| Verdicts | `constructs` 16 | `constructs` 16 | **`constructs` 16** |
| Calls with a flag / flags | 4 / 5 | 4 / 5 | 4 / 5 |
| Non-`.py` lines naming either | 89 | 292 | 290 |
| Test modules naming either | 0 | 1 | 1 |

The handler-spelling table now has four rows: the 12 lookup-only sites as before, and for the four
compute sites two rows of two. `main.py:385` and `:717` (`pipeline_store_handler`,
`inflaton_trajectory_store_handler`) show `store_handler` set; `main.py:493` and `:1089` (the two
that lost the keyword) show it **absent (—)**, with `persist_handler`, `validation_handler` and
`label_builder` still set. The calls and their lines at the throwaway commit are: `main.py:223`,
`:251`, `:318`, `:385`, `:446`, `:493`, `:589`, `:717`, `:868`, `:897`, `:961`, `:1012`, `:1038`,
`:1089`; `plot_GradientCoupledSolutions.py:939`; `plot_InstantonSolutions.py:1172` (the lines below
`:412` move by −1 to −6 against the re-measure, as the deletions above them).

The non-`.py` count falls from 292 to 290: by directory, `.claude/` 17 to 18 (the rewritten rule
names the package in more lines), `.documents/` 55 to 53, and `CLAUDE.md` 1 to 0; `.prompts/` is
unchanged at 219.

`git ls-tree db29b7ffa061e60788ebe3975ec4b45f28daed1d RayTools` prints nothing.

**The flags, by hand** (the script replaced each non-literal size by 1):

| Call (throwaway line) | Keyword | Value |
|---|---|---|
| `main.py:385` | `max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED` (`:398`) | `MAX_INFLIGHT_PIPELINE // 3` (`main.py:80`) = `50 // 3` = 16; at least 1 |
| `main.py:493` | `max_task_queue=MAX_INFLIGHT_PIPELINE` (`:505`) | 50 (`main.py:62`) |
| `main.py:1089` | `max_task_queue=MAX_INFLIGHT_PIPELINE` (`:1103`) | 50 |
| `main.py:717` | `create_batch_size=len(traj_payloads)`, `process_batch_size=len(traj_payloads)` (`:728-729`) | the number of models (below) |

`traj_payloads` has one entry per `model_data` in `model_list` (`main.py:704-715` in the tree; the
comprehension's last line `for model_data in model_list`). `model_list` reaches `run_all_pipelines`
(`def` at `main.py:669`, `model_list: List[dict]` at `:671`) from the one call, `run_all_pipelines(` at
`main.py:1207` (`git grep "run_all_pipelines("` finds no other call outside the tests), with
`model_list = inputs["model_list"]` (`main.py:1149`). `inputs` is `build_pipeline_inputs`'s result
(`config/pipeline_setup.py:114`, `"model_list": model_list` at `:126`), where
`model_list = build_model_list(pool, units, args)`. `build_model_list` (`config/model_list.py:5`):
- **Quadratic:** `m_sample` is `sorted(args.m_values_Mp)` when `len(args.m_values_Mp) > 0` (at least
  one value), otherwise `np.logspace(…, n, …)` with `n = max(1, round(…))` (at least 1). One model is
  appended per `m_sample` value;
- **Quartic:** the same, with `lambda_values` and `n = max(1, round(…))`;
- **anything else** raises `ValueError(f"Unknown potential type: …")`.

So `model_list` has at least one entry, `len(traj_payloads) >= 1`, and the construction at `:717`
(`:720` in the tree before the change) never meets `v0.2.0`'s refusal of a size below 1.
`git diff --stat 7bb3efd HEAD -- config/model_list.py config/pipeline_setup.py` is empty: the reading
is the checklist's, at the current lines.

### §2.3.3 — the imports resolve, without running a driver

`import_check.py`, kept in full below. It parses the three drivers with `ast`; for every `import`
and `from … import` (any depth, absolute) it finds the module with `importlib.util.find_spec`
(counting a namespace package with no file as unresolved); for a `from` import it imports the
module and checks the name is an attribute, or a submodule by `find_spec(f"{X}.{Y}")`; it lists every
name beginning with `_` imported from `raypoolkit` or a submodule (the private-name count); and it
reports `ray.is_initialized()`. It runs from the repository root with `python -I` (repo root added by
path), never executes a driver, and exits 1 on any failure or private name.

```python
"""Resolve every import of the three drivers without running a driver.

usage: import_check.py [--block NAME]   (run from the repository root)
"""
import ast, importlib, importlib.util, sys

REPO = "/Users/ds283/Documents/Code/StochasticInstantons"
DRIVERS = ["main.py", "plot_InstantonSolutions.py", "plot_GradientCoupledSolutions.py"]
sys.path.insert(0, REPO)
if "--block" in sys.argv:                       # breakage 4: make a package unavailable
    sys.modules[sys.argv[sys.argv.index("--block") + 1]] = None

import ray

failures, private, total = [], [], 0


def resolves(name):
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError, AttributeError) as e:
        return None, f"find_spec raised {type(e).__name__}: {e}"
    if spec is None:
        return None, "find_spec found nothing"
    if spec.origin is None and spec.loader is None:   # namespace package
        return None, "namespace package only (no __init__/module file)"
    return spec, "ok"


for drv in DRIVERS:
    tree = ast.parse(open(f"{REPO}/{drv}").read(), filename=drv)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                total += 1
                spec, why = resolves(a.name)
                if spec is None:
                    failures.append((drv, node.lineno, f"import {a.name}", why))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mod = node.module
            spec, why = resolves(mod)
            for a in node.names:
                total += 1
                if spec is None:
                    failures.append((drv, node.lineno, f"from {mod} import {a.name}", why))
                    continue
                if a.name == "*":
                    continue
                if mod.split(".")[0] == "raypoolkit" and a.name.startswith("_"):
                    private.append((drv, node.lineno, mod, a.name))
                try:
                    m = importlib.import_module(mod)
                except Exception as e:
                    failures.append((drv, node.lineno, f"from {mod} import {a.name}",
                                     f"importing {mod} raised {type(e).__name__}: {e}"))
                    continue
                if hasattr(m, a.name):
                    continue
                sub, _ = resolves(f"{mod}.{a.name}")   # Y a submodule of X
                if sub is None:
                    failures.append((drv, node.lineno, f"from {mod} import {a.name}",
                                     f"{a.name!r} is not an attribute of {mod}"))

print(f"imports checked: {total} in {len(DRIVERS)} drivers")
for f in failures:
    print("UNRESOLVED %s:%d  %s  -- %s" % f)
print(f"unresolved: {len(failures)}")
print(f"private names imported from raypoolkit: {len(private)}", private)
rp = importlib.util.find_spec("raypoolkit") if sys.modules.get("raypoolkit", 1) is not None else None
print("raypoolkit origin:", rp.origin if rp else None)
print("ray.is_initialized():", ray.is_initialized())
sys.exit(1 if (failures or private) else 0)
```

Output, on the tree of the commit (exit 0):

```text
imports checked: 159 in 3 drivers
unresolved: 0
private names imported from raypoolkit: 0 []
raypoolkit origin: /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/raypoolkit/__init__.py
ray.is_initialized(): False
```

(`raypoolkit` resolves to the venv's `site-packages/raypoolkit/__init__.py`, the 03 install, not a
checkout.)

### §2.3.4 — `py_compile`

`./venv/bin/python -m py_compile main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py`:
exit 0, no output.

### §2.3.5 — W3 by `ast`

`w3_check.py` (kept in full below), run on the tree of the commit with `python -I`:
- lists every `RayWorkPool(...)` call's `store_handler` keyword: `None` at the 12 lookup-only sites,
  `pipeline_store_handler` at `:385`, `inflaton_trajectory_store_handler` at `:717`, and **absent** at
  `:493` and `:1089`;
- asserts that every `store_handler` keyword anywhere in `main.py` is one of those three values;
- asserts `_run_instanton_queue`'s parameters are `HEAD`'s (`git show HEAD:main.py`) less
  `store_handler`, and that its three callers pass keywords only, none `store_handler`;
- asserts the name `_default_store_handler` is not in `main.py`'s text.

```python
import ast, subprocess
REPO = "/Users/ds283/Documents/Code/StochasticInstantons"
src = open(f"{REPO}/main.py").read()
tree = ast.parse(src)
# 1. every store_handler keyword on a RayWorkPool call
rows = []
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "RayWorkPool":
        kw = {k.arg: k.value for k in n.keywords}
        sh = kw.get("store_handler")
        rows.append((n.lineno, "absent" if sh is None else ast.unparse(sh)))
for r in rows: print("RayWorkPool call", r)
other = [r for r in rows if r[1] not in ("absent", "None")]
print("calls passing a non-None store_handler:", other)
assert [r[1] for r in other] == ["pipeline_store_handler", "inflaton_trajectory_store_handler"], other
# no store_handler keyword passed to anything else
kws = [(n.lineno, ast.unparse(k.value)) for n in ast.walk(tree) if isinstance(n, ast.Call)
       for k in n.keywords if k.arg == "store_handler"]
print("all store_handler keywords in main.py:", kws)
assert {v for _, v in kws} == {"None", "pipeline_store_handler", "inflaton_trajectory_store_handler"}, kws
name_in_src = "_default_store_handler" in src
print("keyword checks (store_handler arguments) passed; name _default_store_handler in main.py source:", name_in_src)
# 2. _run_instanton_queue's parameters, against the committed HEAD
def params(text):
    t = ast.parse(text)
    f = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "_run_instanton_queue")
    return [a.arg for a in f.args.args]
old = params(subprocess.check_output(["git", "-C", REPO, "show", "HEAD:main.py"], text=True))
new = params(src)
print("old:", old); print("new:", new)
assert new == [p for p in old if p != "store_handler"] and "store_handler" in old
# 3. every call to it: keywords only, none named store_handler, none positional beyond the helper's own
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_run_instanton_queue":
        print("call at", n.lineno, "positional:", len(n.args), "keywords:", [k.arg for k in n.keywords])
        assert all(k.arg in new for k in n.keywords)
assert not name_in_src, "_default_store_handler still named in main.py"
print("W3 OK")
```

Output (exit 0):

```text
RayWorkPool call (223, 'None')
RayWorkPool call (251, 'None')
RayWorkPool call (318, 'None')
RayWorkPool call (385, 'pipeline_store_handler')
RayWorkPool call (446, 'None')
RayWorkPool call (493, 'absent')
RayWorkPool call (589, 'None')
RayWorkPool call (717, 'inflaton_trajectory_store_handler')
RayWorkPool call (868, 'None')
RayWorkPool call (897, 'None')
RayWorkPool call (961, 'None')
RayWorkPool call (1012, 'None')
RayWorkPool call (1038, 'None')
RayWorkPool call (1089, 'absent')
calls passing a non-None store_handler: [(385, 'pipeline_store_handler'), (717, 'inflaton_trajectory_store_handler')]
all store_handler keywords in main.py: [(223, 'None'), (251, 'None'), (318, 'None'), (385, 'pipeline_store_handler'), (446, 'None'), (589, 'None'), (717, 'inflaton_trajectory_store_handler'), (868, 'None'), (897, 'None'), (961, 'None'), (1012, 'None'), (1038, 'None')]
keyword checks (store_handler arguments) passed; name _default_store_handler in main.py source: False
old: ['pool', 'cls_name', 'task_list', 'key_fields', 'full_payload', 'shard_key_of', 'label_builder', 'title', 'store_handler', 'no_store_values']
new: ['pool', 'cls_name', 'task_list', 'key_fields', 'full_payload', 'shard_key_of', 'label_builder', 'title', 'no_store_values']
call at 655 positional: 0 keywords: ['pool', 'cls_name', 'task_list', 'key_fields', 'full_payload', 'shard_key_of', 'label_builder', 'title', 'no_store_values']
call at 811 positional: 0 keywords: ['pool', 'cls_name', 'task_list', 'key_fields', 'full_payload', 'shard_key_of', 'label_builder', 'title']
call at 834 positional: 0 keywords: ['pool', 'cls_name', 'task_list', 'key_fields', 'full_payload', 'shard_key_of', 'label_builder', 'title']
W3 OK
```

### §2.3.6 — the suites

Serially, in the foreground, no Ray cluster up (`pgrep` finds none), `RAY_ADDRESS` unset for the
default run, no `slow` block (the diff touches none of its paths; `picard.py` is not edited).

| Run | Result | Time | Load (1/5/15 min) |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **680: 679 passed, 1 skipped** (130 deselected; 10 warnings) | 49.79 s | 43.4 / 24.6 / 27.1 before; 32.8 / 25.4 / 27.2 after |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **61: 60 passed, 1 skipped** (749 deselected; 1 warning) | 21.50 s | 32.8 / 25.4 / 27.2 before; 47.4 / 28.9 / 28.5 after |

Both equal 03's counts (680 and 61). Three default-suite modules import a plot driver at
collection (`tests/test_plot_adapters_golden.py:49`, `tests/test_plot_extraction_golden.py:59`,
`tests/test_plot_gradient_coupled_driver.py:43`), so they execute `from raypoolkit import
RayWorkPool` for two of the three drivers; no test imports `main.py`, so its import is checked by
`ast` alone. No test imports or constructs `RayTools` or `RayWorkPool`
(`tests/test_rehearsal_stage_counts.py` names the path in a docstring). The integration run is the
first through the package: it constructs no `RayWorkPool` and imports nothing from `RayTools`.

### Other

- **The venv is as 03 left it:** `pip freeze` differs from `measure/out/7bb3efd-pip-freeze.txt` by the
  one line `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`.
  Nothing installed or uninstalled.
- **RayPoolKit** was only read and run: `git status --short` there is empty after every run, `HEAD`
  `17029d9`.
- **No Ray cluster** was started by the agent; `ray start` and `ray stop` were not run; no driver was
  run or imported by my scripts (`ray` is imported by the check, and `ray.is_initialized()` is `False`);
  no store was opened.
- **W5 against the package.** Every corrected statement agrees with `raypoolkit/RayWorkPool.py` at
  `v0.2.0` (`git -C RayPoolKit show v0.2.0:raypoolkit/RayWorkPool.py`): `:385` is `if obj.available:`
  (inside `if hasattr(obj, "available"):`, `:384`); `:424-426` is `compute_task: ObjectRef =
  self._compute_handler(obj, **compute_args)`; `:75-76` is `_default_compute_handler` returning
  `obj.compute(**kwargs)`; `:471` is `self._store_handler(obj, self._pool)`; `:79-80` is
  `_default_store_handler` calling `obj.store()`; `:481` is `self._persist_handler(obj, self._pool)`.
  `requirements.txt:58` holds the pin.

## The deliberate-breakage record

Each applied to the working tree of the tree at `ef13445`, shown to be caught, and reverted by
`git apply -R`. The recorded diffs replay with `git apply` from a clean tree at `ef13445`
(checked with `git apply --check` and `git apply -R --check` after committing). None is committed.

### Breakage 1 — `main.py`'s import reverted to the deleted module

```diff
diff --git a/main.py b/main.py
index 30e1573..9ba0971 100644
--- a/main.py
+++ b/main.py
@@ -44,3 +44,3 @@ from InflationConcepts import (
 from MetadataConcepts import store_tag, tolerance
-from raypoolkit import RayWorkPool
+from RayTools.RayWorkPool import RayWorkPool
 from Units import Planck_units
```

- **Import check:** exit 1: `UNRESOLVED main.py:45  from RayTools.RayWorkPool import RayWorkPool  --
  find_spec raised ModuleNotFoundError: No module named 'RayTools'`; `unresolved: 1`. (The module is
  gone; no `RayTools` directory survives to make a namespace package.)
- **The script, at a throwaway commit** (`1c74186…`): `Imports of a RayTools module | 1`
  (`main.py:45`, `from RayTools.RayWorkPool import RayWorkPool`, no private name); `RayTools/` table
  empty; 16 calls, `constructs` 16.
- `py_compile` does **not** catch it (exit 0): the import is only evaluated at run time.

### Breakage 2 — the plot script's import misspelled

```diff
diff --git a/plot_InstantonSolutions.py b/plot_InstantonSolutions.py
index c4fdea6..aab6f80 100644
--- a/plot_InstantonSolutions.py
+++ b/plot_InstantonSolutions.py
@@ -71,3 +71,3 @@ from plotting.provenance import VERSION_LABEL, _provenance_footer
 from plotting.sampling import _evenly_sample, _safe_name, _safe_num
-from raypoolkit import RayWorkPool
+from raypoolkit import RayWorkPoool
 from Units import Planck_units
```

- **Import check:** exit 1: `UNRESOLVED plot_InstantonSolutions.py:72  from raypoolkit import
  RayWorkPoool  -- 'RayWorkPoool' is not an attribute of raypoolkit`; `unresolved: 1`.
- The script at its throwaway commit (`a802687…`) reports 0 imports of `RayTools` (the import is of
  `raypoolkit`, outside its scope) and 16 calls: **the script does not catch it**.
- `py_compile` does not catch it (exit 0).
- **The suites catch it:** with the mutation applied, `pytest tests/test_plot_adapters_golden.py
  tests/test_plot_extraction_golden.py --collect-only` gives `ImportError: cannot import name
  'RayWorkPoool' from 'raypoolkit'` and `2 errors during collection` (both modules import
  `plot_InstantonSolutions`); reverted afterwards.

### Breakage 3 — the private name restored

```diff
diff --git a/main.py b/main.py
index 30e1573..edd5f68 100644
--- a/main.py
+++ b/main.py
@@ -45,2 +45,3 @@ from MetadataConcepts import store_tag, tolerance
 from raypoolkit import RayWorkPool
+from raypoolkit.RayWorkPool import _default_store_handler
 from Units import Planck_units
```

What each check says, exactly (the orchestrator's correction 7: **the script does not report it**):
- **RayPoolKit's script** at its throwaway commit (`0270097…`): `Imports of a RayTools module | 0`,
  `… naming a private name | 0`, 16 calls, `constructs` 16. It does not see it, since
  `raypoolkit.RayWorkPool` is not a `RayTools` module.
- **The import check:** exit 1, `imports checked: 160`, `unresolved: 0`, and
  `private names imported from raypoolkit: 1 [('main.py', 46, 'raypoolkit.RayWorkPool', '_default_store_handler')]`.
  (The name does resolve: the module is reachable at `v0.2.0`, as the checklist says.)
- **`git grep -n _default_store_handler -- main.py`:** `main.py:46:from raypoolkit.RayWorkPool import _default_store_handler`.
- **§2.3.5's check (`w3_check.py`):** unaffected as to the keywords: every `store_handler` keyword
  assertion and the `_run_instanton_queue` parameter assertion pass, and it prints `name
  _default_store_handler in main.py source: True`; its last assertion, the name's absence from the
  source, then fails. (That last assertion is mine, beyond the prompt's §2.3.5, which concerns the
  keyword.)
- `py_compile` does not catch it (exit 0).

### Breakage 4 — `raypoolkit` made unavailable, without uninstalling it

A command, not a diff: the import check run with `sys.modules["raypoolkit"] = None` set before the
parsing (`--block raypoolkit`):

```text
$ ./venv/bin/python -I import_check.py --block raypoolkit
imports checked: 159 in 3 drivers
UNRESOLVED main.py:45  from raypoolkit import RayWorkPool  -- find_spec found nothing
UNRESOLVED plot_InstantonSolutions.py:72  from raypoolkit import RayWorkPool  -- find_spec found nothing
UNRESOLVED plot_GradientCoupledSolutions.py:100  from raypoolkit import RayWorkPool  -- find_spec found nothing
unresolved: 3
private names imported from raypoolkit: 0 []
raypoolkit origin: None
ray.is_initialized(): False
```

(exit 1; all three drivers fail. `find_spec` reports "found nothing" for a name blocked by `None` in
`sys.modules` here.)

After the four, `git status` shows only the staged change and the records; `git diff` of the
drivers against the index is empty.

## Observations not acted on

- **`picard.py:450-456`** (a July comment, `b5a3a9f`) says `RayTools/RayWorkPool.py` "is protected
  infrastructure (CLAUDE.md)" and has no per-task timeout hook. The path is gone and the pool is not
  SI's to protect; the substance holds (no `timeout` or `cancel` in `raypoolkit/RayWorkPool.py` at
  `v0.2.0`). It is not edited (a `ComputeTargets/` file is outside the prompt's §5 list and would
  widen the suites to the `slow` block). Opened: `[pool-prose-stale-after-raypoolkit-adoption]`, owner 12.
- **The constructor sketches** at `INFRASTRUCTURE.md:357-373` and `architecture-summary.md:328-344`
  give `create_batch_size=10`, `process_batch_size=10`, `max_task_queue=50` as defaults. The copy's
  and the package's are both 5, 1 and 200 (`DEFAULT_*`, `:26-29` in each; the package's
  keywords equal the copy's, in the same order). Wrong before 04, not made false by it; the same
  issue.
- **`utilities.format_time`**, which the copy imported (`:24`), is also imported by
  `Datastore/SQL/ProfileAgent.py:26` and `Quadrature/simple_quadrature.py:27`; it stays and is not touched.
- **The board's "Code:" line** (its header) still lists `RayTools/` among the campaign's code, as the
  campaign's history; not edited.
- **Import order.** `from raypoolkit import RayWorkPool` sits where the old line was, between
  `MetadataConcepts` and `Units` in `main.py` and the plot scripts (deviation 10).
- **Dated records** naming `RayTools/RayWorkPool.py` (`gradient-coupled-instanton/24-…:75` and the rest
  of the checklist's item 9 list), this campaign's results notes, `verification.md` and every line
  under `.prompts/` are left as they are.
- **The ignored `__pycache__`** under the old `RayTools/` was removed by hand because it kept the
  directory alive after `git rm`; `py_compile` of the three drivers creates `__pycache__/` entries
  of their own (ignored).

## The text of the RayPoolKit G4 record, for 12 to carry into its draft

> **G4 — StochasticInstantons adopts `raypoolkit` `v0.2.0`. Holds, 2026-10-20.** StochasticInstantons
> (SI), campaign `dk-and-rpk-migration`, prompt 04, commit `ef13445` on branch
> `dk-and-rpk-migration` (on `9a7cb50`; the pin is `5396a3d`). By checklist item 8, items 1–5:
> 1. **`RayTools/` is gone.** `git ls-tree <commit> RayTools` is empty, and no `RayTools` directory is
>    left in the working tree.
> 2. **No import of it, and none of `_default_store_handler`.** `measure_client_pools.py si --commit`
>    at a commit of the staged tree (`db29b7f`, built by `git commit-tree` on no branch) reports 0
>    imports of a `RayTools` module, 0 private names, 0 `import_module` / `__import__` calls, and
>    `RayTools/` empty. It reports **2 string literals** naming `RayTools`: the module docstrings of
>    `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py` (line 16) and
>    `tests/test_rehearsal_stage_counts.py` (line 16), dated statements about the parser's fixtures
>    that are not imports and were left unedited; and 1 test module naming it (that docstring's `:22`).
>    The script looks only at `RayTools`, so it cannot see a private `raypoolkit` name: SI's own `ast`
>    check of the three drivers finds 0 names beginning with `_` imported from `raypoolkit`, and
>    `git grep _default_store_handler -- main.py` is empty. (Option (a) of item 3 was taken: seven lines
>    of `main.py`.)
> 3. **The pin** `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0` is in `requirements.txt`
>    (`:58`), and the venv is installed from it, not editable: `direct_url.json` records commit
>    `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, requested `v0.2.0`, the four modules byte-equal to the
>    tag's (SI's prompt 03).
> 4. **SI's suites pass:** the default run 680 (679 passed, 1 skipped) and the integration run 61 (60
>    passed, 1 skipped), as before the change.
> 5. **Every site constructs:** the script at that commit finds **16** calls, every one `constructs`;
>    its 5 flags (on 4 calls: `MAX_INFLIGHT_PIPELINE_UNIFIED` = 16, `MAX_INFLIGHT_PIPELINE` = 50 twice,
>    `len(traj_payloads)` twice) were checked by hand, and `model_list` is never empty
>    (`config/model_list.py` makes at least one model per sampled value or raises).
>
> Not yet: item 6 (this record, on RayPoolKit's own board, a commit in that repository); and the run
> under real Ray, which SI's prompt 07 (RH1) makes. No driver ran and no Ray started in 04.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, `ef13445` on `9a7cb50`. Tracked changes: `RayTools/` deleted
  (2 files); `main.py`, `plot_GradientCoupledSolutions.py`, `plot_InstantonSolutions.py`; `CLAUDE.md`,
  `.claude/rules/ray-dispatch.md`, `.documents/FILE_MAP.md`, `.documents/INFRASTRUCTURE.md`,
  `.documents/architecture-summary.md`; `.documents/OPEN-ISSUES.md`; the board; this note.
- **The pool is the package's.** All three drivers `from raypoolkit import RayWorkPool`; the 16 sites
  construct under `v0.2.0` (the script, at the throwaway commit, 16 of 16 `constructs`). Two compute
  sites (`_run_instanton_queue`'s at `main.py:493`, and the STAGE 4 construction at `:1089`) no longer
  pass `store_handler`: the package's default, `obj.store()`, is what the copy's `_default_store_handler`
  was. **No driver has run on this tree**; 07's RH1 is the first run through the package under real Ray,
  and it expects every driver to print
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **`RayTools/` is gone**, including the ignored `__pycache__`. `DatastoreKit`'s rewrite list loses
  `RayTools/RayWorkPool.py:23` (README U1); no U12 exception is needed (09).
- **Protected list:** `CLAUDE.md:101` is `Datastore/SQL/ShardedPool.py` alone; 12 rewrites the section.
- **The issue** `[pool-prose-stale-after-raypoolkit-adoption]` is open, owner 12
  (`.documents/OPEN-ISSUES.md` §6a; 61 open). `.prompts/INDEX.md` is the orchestrator's.
- **RayPoolKit G4** is recorded on the board as holding by items 1–5. Item 6 (the record on
  RayPoolKit's board) is 12's draft (P14); RH1 (07) adds the run under real Ray. The text is above.
- **Suites:** 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped); `slow` baseline 69 of 69
  (02's S1). 05's, 06's and 07's suites start from these.
- **The venv** is as 03 left it (`pip freeze` is `measure/out/7bb3efd-pip-freeze.txt` plus the one
  `raypoolkit` line); `pip check` was not needed, nothing installed. No Ray cluster is up, the
  rehearsal lock is untouched, no store was opened.
- **Rollback:** `git revert` of `ef13445`. The venv needs nothing.
