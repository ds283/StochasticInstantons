In this prompt, the target is to assemble a sample of source files that can be uploaded to an
online Claude.ai session, as context.

Please:

1. If it does not already exist, createa a directory `claude-context` in the top level of the repository. If this
   directory already exists, you will need to remove the current contents. There is no need to save any of these files,
   which are ephemeral copies of files elsewhere in the source tree. The exception are the files `FILE_MAP.md`,
   `NUMERICAL_SCHEMES.md`, and `INFRASTRUCTURE.md` if they are present. `FILE_MAP.md` describes the files copied into
   the `claude-context` folder and their provenance (see below). You can use this as the basis of a new version.
   `NUMERICAL_SCHEMES.md` is a narrative explanation of how the numerical implementation for `SlowRollInstanton`,
   `FullInstanton`, and `GradientCoupledInstanton` work. `INFRASTRUCTURE.md` is similar for the non-numerical,
   non-physics Datastore (SQL database) and Ray work pool (parallel dispatch) layers. You can keep these files if no
   updates are needed.
2. Review the source files and build a selection that illustrates the main elements of the pipeline and its numerical
   machinery. Please include at least:
    - A representative sample of `ComputeTarget` elements, including all three key instanton targets,
      `SlowRollInstanton`, `FullInstanton` and `GradientCoupledInstanton`. For `GradientCoupledInstanton` there are a
      number of implementation files for specific elements of the (complicated) numerical method. Please also include
      the `CompactionFunction` compute target.
    - Relevant source files from the `config` folder, including at least `sharding.py` which explains the sharded
      database configuration
    - A representative sample of files from `CosmologyConcepts`, including at least the critical `AbstractPotential`
      interface
    - A representative sample of files from the `CosmologyModels` folder
    - Source files illustrating how the complex Datastore layer works. Include `Datastore/object.py`,
      `Datastore/SQL/Datastore.py` and the sharded pool implementation `Datastore/SQL/ShardedPool.py`. Please also
      include a representative sample of object factories from `Datastore/SQL/ObjectFactories`. At a minimum, please
      include factories for the key instanton compute targets `SlowRollInstanton`, `FullInstanton`,
      `GradientCoupledInstanton` and `CompactionFunction`.
    - Concepts needed from `InflationConcepts`, `Interpolataion`, `MetadataConcepts`, `Numerics`, `Quadrature` to
      illustrate the numerical implementation
    - The `RayWorkPool.py` abstraction from `RayTools`
    - The main driver scripts `main.py`, `plot_InstantonSolutions.py` and `regression_InstantonOutputs.py`
    - The exemplar parameter file `quadratic-minimal.yaml`
3. Copy the representative files to the `claude-context` folder in a flat structure. You will need to systematically
   rename files so that source files with the same name as distinguishable. Claude.ai does not cope with uploaded files
   that have duplicate names. Produce a mapping file `FILE_MAP.md` that explains how these renamed files relate to the
   original files in the source tree
4. Produce a narrative explanation (stored in `NUMERICAL_SCHEMES.md`) of how the
   `SlowRollInstanton`, `FullInstanton`and `GradientCoupledInstanton` numerical schemes work. Explain the Picard
   iteraction structure used for `FullInstanton` and `GradientCoupledInstanton` (so we can solve for the response fields
   on a backwards pass) and explain its value (the noise fields have unwanted growing modes in a forward
   implementation). Explain the collocation scheme used to solve `GradientCoupledInstanton` and the discretization of
   the differential operator. Explain the transformation to the onion coordinate `y`. You can refer to the details in
   the `./.documents/onion_model.tex` mathematical notes, and you can assume the online Claude.ai will have access to
   these notes. Explain the scheme used to assign scales to shells in `GradientCoupledInstanton` and how it relates to
   the scheme used by `FullInstanton` + `CompactionFunction`.
5. Produce a narrative explanation (stored in `INFRASTRUCTURE.md`) of how the `Datastore`, `ShardedPool`, and
   `RayWorkPool` abstractions work.

The contents of the `claude-context` folder are ephemeral and are regenerated when necessary. Do not commit anything to
the git repository.
