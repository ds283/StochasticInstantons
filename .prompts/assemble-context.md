## SUMMARY

In this prompt, the targets are:

- to assemble a sample of source files that can be uploaded to an online Claude.ai session, as context
- to produce (or update) a map of these files, to guide Claude.ai's reasoning
- to prouduce (or update) a narrative explanation of the numerical schemes and infrastructure used in the pipeline

### PREPARATION

1. If it does not already exist, create a directory `claude-context` in the top level of the repository. If this
   directory already exists, you will need to remove the current contents. There is no need to save any of these files,
   which are ephemeral copies of files elsewhere in the source tree.
2. Inspect the `./.documents` folder to determine whether there are `FILE_MAP.md`, `NUMERICAL_SCHEMES.md` and
   `INFRASTRUCTURE.md` files. If these are present, use these as a base for the steps below, but be aware thate these
   files may be stale and require updates.

### PREPARE SOURCE FILE CONTEXT BUNDLE AND UPDATE `FILE_MAP.md`

3. Working from `FILE_MAP.md` as a guide, if present, review the source files and build a selection that illustrates the
   main elements of the pipeline and its numerical machinery. Please include at least:
    - A representative sample of `ComputeTarget` elements, including all three key instanton targets,
      `SlowRollInstanton`, `FullInstanton` and `GradientCoupledInstanton`. For `GradientCoupledInstanton` there are a
      number of implementation files for specific elements of its complex numerical scheme. Please also include
      the `CompactionFunction` compute target, which is a key driver of the science output.
    - Relevant source files from the `config` folder, including at least `sharding.py` which explains the sharded
      database configuration
    - A representative sample of files from `CosmologyConcepts`, including at least the critical `AbstractPotential`
      interface
    - A representative sample of files from the `CosmologyModels` folder
    - Concepts needed from `InflationConcepts`, `Interpolataion`, `MetadataConcepts`, `Numerics`, `Quadrature` to
      illustrate the numerical implementation. You should include an example of a concrete model implementing the
      `AbstractPotential` interface; `QuadraticPotential` is a good candidate. You should also include the
      `AbstractDiffusionModel` concept and an example of a concrete model implementing it, such as
      `MasslessDecoupledDiffusion`.
    - Source files illustrating how the complex Datastore layer works. Include `Datastore/object.py`,
      `Datastore/SQL/Datastore.py` and the sharded pool implementation `Datastore/SQL/ShardedPool.py`. Please also
      include a representative sample of object factories from `Datastore/SQL/ObjectFactories`. At a minimum, please
      include factories for the key instanton compute targets `SlowRollInstanton`, `FullInstanton`,
      `GradientCoupledInstanton` and `CompactionFunction`.
    - The `RayWorkPool.py` abstraction from `RayTools`
    - The main driver scripts `main.py`, `plot_InstantonSolutions.py` and `regression_InstantonOutputs.py`
    - The exemplar parameter file `quadratic-minimal.yaml`
    - Examples of any tests in `./tests` that you consider to be relevant.
4. Copy the representative files to the `claude-context` folder in a flat structure. You will need to systematically
   rename files so that source files with the same name as distinguishable. Claude.ai does not cope with uploaded files
   that have duplicate names.
5. If needed, **update in place** the mapping file `./.documents/FILE_MAP.md` that explains how these renamed files
   relate to the original files in the source tree. **Commit** your changes to the respository. Then copy the final
   `FILE_MAP.md` to the `claude-context` folder.

### NARRATIVE SUMMARIES `NUMERICAL_SCHEMES.md` AND `INFRASTRUCTURE.md`

6. Working from a stored version in `./.documents` as a guide, if present, produce a narrative explanation (stored in
   `NUMERICAL_SCHEMES.md`) of how the numerical schemes implemented by `SlowRollInstanton`, `FullInstanton`,
   `CompactionFunction` and `GradientCoupledInstanton`  work.
    - Critically, eplain the `UnitsLike` concept and the units discipline used throughout the codebase: we work in
      natural units where `c = hbar = 1`,
      so all physical quantites have dimensions of mass or inverse mass. **Dimensionful** quantities need to be
      specified in conjunction with an appropriate unit from a `UnitsLike` instance (such as `Planck_units` or
      `GeV_units`).
    - Explain the Picard iteration structure used for `FullInstanton` and `GradientCoupledInstanton` (so we can solve
      for the response fields on a backwards pass) and explain its purpose (the noise fields have unwanted growing
      modes in a forward implementation).
    - Explain the collocation scheme used to solve `GradientCoupledInstanton` and the discretization of
      the differential operator.
    - Explain the SBP/SAT scheme used to regularize the discrete differential operator. The prevents spurious
      instabilities driven by unphysical energy inflow at the spatial boundaries (here the core boundary – the fact the
      advection is zero at the exterior boundary means there is no inflow there).
    - Explain the transformation to the onion coordinate `y`.
    - Explain the scheme used to assign scales to shells in `GradientCoupledInstanton` and how it relates
      to the scheme used by `FullInstanton` + `CompactionFunction`.
    - You can use the Markdown-format implementation notes and design documents in the
      `./.documents/gradient-coupled-instanton` folder. However, you **should no**t assume that the Claude.ai model will
      have direct access to these. Use them as input to drive your summary, but do not refer to them.
    - However, you **can** use the mathematical notes `./.documents/gradient-coupled-instanton/onion_model.tex`, which
      provides the physics derivation of the onion model, and you **can** assume the online Claude.ai will have access
      to these notes.
7. If `./documents/NUMERICAL_SCHEMES.md` is present, **update in place** as needed rather than writing a completely new
   narrative from scratch. **Commit** your changes to the repository. Then copy the final `NUMERICAL_SCHEMES.md` to the
   `claude-context` folder.
8. Working from a stored version in `./documents` as a guide, produce a narrative explanation of how the `Datastore`
   and `RayWorkPool` concepts work.
    - Explain the `DatastoreObject` base class for all models that are persisted in the datastore.
    - Explain the underlying SQL persistence layer, the query model for lookup, and how this mints/persists new objects
      when needed.
    - Explain the persistence discipline for dimensionful quantities: a sensible unit is chosen to serialize to the
      database; quantities are converted into this unit before writing out, and must be rehydrated with the correct
      unit. This allows the compute layer to use different units, while always serializing consistent results into the
      database. Also, stored results in the database retain their value even if we elect to change the units used for
      computation.
    - Explain the factory class pattern and describe the main responsibilities of a factory class (registration, build,
      store, validation, inventory, `read_table`).
    - Explain the `ShardedPool` concept and how it builds over a pool of `Datastore` actors
    - Explain the `RayWorkPool` abstraction, including the unit of work (lookup -> compute -> store -> validate) and how
      custom drivers can be used to modify this if needed. Illustrate your explanation with examples drawn from the
      orchestration scripts.
9. If `./documents/INFRASTRUCTURE.md` is present, **update in place** as needed rather than writing a completely new
   narrative from scratch. **Commit** your changes to the repository. Then copy the final `INFRASTRUCTURE.md` to the
   `claude-context` folder.

**Note.** The contents of the `claude-context` folder are **ephemeral** and are regenerated when necessary. **Do not**
commit **anything** in the `claude-context` folder to the git repository.
