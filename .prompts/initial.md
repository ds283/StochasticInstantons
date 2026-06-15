## Overview

I am building a parallelized code to compute stochastic instantons describing noise-driven transitions in models of
early-universe inflation.

I would like to re-use elements from a similar code. You can find an architectural summary of this code in the
file `architecture-summary.md` in the project files area. I have also uploaded a number of representative source
files that exemplify how different aspects of the code work in practice. The main layers of interest are:

- distributed multiprocessing using Ray and the `RayWorkerPool` abstraction
- SQL backed datastore abstraction using the `Datastore` and `ShardedPool` abstractions and their surrounding
  infrastructure, which are used to store results. For some, like `redshift`, which are effectively constants, this is
  done by store-on-lookup: a constant is exchanged for a database key that represents the persisted value. For others
  that require computation such as `ScalarModel` there is a multiple step lookup--compute--store cycle. Lookup returns a
  proxy object representing the uncomputed value, almost a form of "future"; a compute step populates its values; a
  store step emplaces these into the database.
- the "unit of work" concept represented by the lookup--compute--store cycle

Also, the file `plot_ScalarModel.py` is critical, because it shows how stored values in the database can be looked up
and marshalled to produce science outputs.

## Target code

The code being adapted calculates scalar field histories in the late universe. These scalar field models are dark
energy models. They share some features with early universe models, including having a potential.

The target is to compute instantons representing transitions between defined field configurations during inflation.

The inflationary model is taken to have canonical kinetic terms and is specified by its potential. A key initial
decision is whether to build the code to support single-field or multiple-field models. Multiple-field models are more
complex, and instantons in these scenarios have not really been explored theoretically. My recommendation is to limit
the scope to single-field models, but I would like to build the code in such a way that the extensions of multiple field
models is considered from the beginning. The major issue here is that I don't see any simple way to build database
tables that are agnostic about the number of fields in the model.

Each potential may contain its own parameters. The existing database layer for dealing with potential is probably
adequate here with only small modifications.

The slow-roll approximation is not used, so each field has a field-space coordinate \phi and a momentum value \pi =
d\phi / dN. The e-folding number N is the sensible time coordinate here, rather than redshift. Notice here N is a number
that increases towards the end of inflation.

In a Martin--Siggia--Rose-type formalism, these fields are doubled. Each gains a "response field" partner that encodes
the noise realization.

The formalism is sketched in my attached paper `main.pdf` (built from the LaTeX source `main.tex`). See Eqs. (4.17a)-(
4.17b) in this paper. The fields P_1, P_2 are the response fields.

Each instanton is defined by boundary conditions:

- the initial field value \phi_init, determined by a starting time at a specified number of e-folds N_init **before**
  the end of inflation.
- the final field value \phi_final, determined by an ending time at a specified number of e-folds N_stop **before** the
  end of inflation. The different N_init - N_final defines a **noiseless transition time** N_trans. This is the natural
  time the transition takes to complete in the absence of stochastic noise. To build the instanton, this boundary
  condition is not applied at the noiseless transition time, but at a time N_init + N_trans + Delta N_\star, defined
  below.
- compatibility with the Schwinger--Keldysh boundary condition at the final time requires that the response field
  conjugate to the field value is zero there
- the remaining boundary condition isn't clearly fixed and represents the field velocity at the initial or final time.
  In the context of a transition during inflation it should probably be allowed to float. One should then marginalize
  over it, or optimize its value to produce the most probable transition. Initially, however, it's reasonable to set the
  initial field velocity to match the value on the slow-roll solution.

We also need the **target excess transition time** \Delta N_\star. Since \Delta N_\star ~ \zeta and we are targeting a
density perturbation of order unity, typical instantons will have \Delta N_\star ~ 1. One purpose of this numerical code
is to explore exactly what kind of density profile we get for different values of \Delta N_\star.

We will want to compute slow-roll instantons between the same field values, in order to compare these to the full
non-slow-roll instantons. This could be done as part of a single unit-of-work with the non-slow-roll instanton, but is
probably better as a separate compute target.

## Compaction functions

In a second step, I would like to estimate what the **spatial configuration** corresponding to the instanton looks like.
To do this, I plan to proceed as follows.

- The end-of-inflation surface defines a fixed scale k_end with k_end = (a H)_end. This maps to a fixed scale in the
  present-day universe. Provided a H decreases as we move backwards during inflation, at each point during inflation the
  horizon scale maps to a different, larger, fixed scale in the present-day universe. At each time on the instanton, we
  assume the instanon describes the central field value in a spherical volume that is undergoing the transition. In each
  time step only the core region continues on the instanton; the outer region detaches in a spherically symmetric way
  (spherically symmetric under the assumptions this is the maximum-probability configuration, as is usual with
  instantons). By computing the excess number of e-folds at each point, we can map out the radial profile of \zeta.
- This prescription only makes sense in a simple attractor model of inflation, where \zeta is conserved outside the
  horizon. Otherwise, we have to track how \zeta evolves from the point where each spacetime region detaches from the
  instanton trajectory.
- Once we have the spatial profile, we can process it to produce the **compaction function**. The compaction function is
  the correct diagnostic to determine whether this perturbation has sharp enough spatial gradients to collapse into a
  primordial black hole, and if so, which scale collapses.
- From the collapse scale we can compute a **mass**, so we can identify the mass of PBH formed by this particular
  density profile. Understanding how this mass relates to the parameters of the transition described by the instanton is
  one of the key targets of this code.

## Building the code

I would like to use Claude Code to perform as much as possible of the mechanical steps of converting (a duplicate of)
the existing code from its chameleon (dark energy) function to the new stochastic instanton function.

Can you evaluate the existing code and identify any issues that need to be addressed?

I would like to iterate on producing a good Claude Code prompt (or series of prompts) that will carry out the necessary
changes.
