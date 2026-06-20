import configargparse


def create_argument_parser():
    parser = configargparse.ArgumentParser(
        description="StochasticInstanton: compute stochastic instantons "
        "in inflationary scalar field models",
        default_config_files=["stochastic_instanton.yaml"],
    )

    # Config file
    parser.add_argument(
        "--config", is_config_file=True, help="Path to YAML configuration file"
    )

    # Database
    db = parser.add_argument_group("Database")
    db.add_argument(
        "--database",
        type=str,
        default=None,
        help="Path to primary SQLite database file (required)",
    )
    db.add_argument(
        "--shards", type=int, default=20, help="Number of database shards (default: 20)"
    )
    db.add_argument(
        "--db-timeout",
        type=int,
        default=60,
        help="SQLite timeout in seconds (default: 60)",
    )
    db.add_argument(
        "--profile-db",
        type=str,
        default=None,
        help="Path to database profiling output file",
    )
    db.add_argument(
        "--job-name",
        type=str,
        default=None,
        help="Optional label for this run, used in profiling output",
    )
    db.add_argument(
        "--prune-unvalidated",
        action="store_true",
        default=True,
        help="Delete unvalidated records from previous incomplete runs",
    )
    db.add_argument(
        "--drop",
        nargs="*",
        default=[],
        choices=[
            "inflaton-trajectory",
            "full-instanton",
            "slow-roll-instanton",
            "compaction-function",
        ],
        help="Drop specified table groups before running",
    )
    db.add_argument(
        "--stop-after",
        nargs="*",
        default=[],
        choices=[
            "inflaton-trajectory",
            "full-instanton",
            "slow-roll-instanton",
            "compaction-function",
        ],
        help="Stop the pipeline after the named stage completes; if multiple are given, stops at the earliest",
    )

    # Ray
    ray_grp = parser.add_argument_group("Ray")
    ray_grp.add_argument(
        "--ray-address",
        type=str,
        default="auto",
        help="Ray cluster address (default: 'auto')",
    )

    # ODE tolerances
    tol = parser.add_argument_group("ODE tolerances")
    tol.add_argument(
        "--abs-tol",
        type=float,
        default=1e-8,
        help="Absolute ODE tolerance (default: 1e-8)",
    )
    tol.add_argument(
        "--rel-tol",
        type=float,
        default=1e-8,
        help="Relative ODE tolerance (default: 1e-8)",
    )

    # Potential
    pot = parser.add_argument_group("Potential")
    pot.add_argument(
        "--potential-type",
        type=str,
        default="Quadratic",
        choices=["Quadratic", "Quartic"],
        help="Inflationary potential type (default: Quadratic)",
    )

    # Quadratic potential: scan over mass m in units of Mp
    pot.add_argument(
        "--log10-m-low-Mp",
        type=float,
        default=-6.0,
        help="Lower bound of log10(m/Mp) grid (default: -6.0)",
    )
    pot.add_argument(
        "--log10-m-high-Mp",
        type=float,
        default=-5.0,
        help="Upper bound of log10(m/Mp) grid (default: -5.0)",
    )
    pot.add_argument(
        "--samples-per-log10-m",
        type=float,
        default=10.0,
        help="Sample points per decade of m/Mp (default: 10)",
    )
    pot.add_argument(
        "--m-values-Mp",
        nargs="*",
        type=float,
        default=[],
        help="Explicit list of m/Mp values (overrides grid)",
    )

    # Quartic potential: scan over coupling lambda (dimensionless)
    pot.add_argument(
        "--log10-lambda-low",
        type=float,
        default=-13.0,
        help="Lower bound of log10(lambda) grid (default: -13.0)",
    )
    pot.add_argument(
        "--log10-lambda-high",
        type=float,
        default=-12.0,
        help="Upper bound of log10(lambda) grid (default: -12.0)",
    )
    pot.add_argument(
        "--samples-per-log10-lambda",
        type=float,
        default=10.0,
        help="Sample points per decade of lambda (default: 10)",
    )
    pot.add_argument(
        "--lambda-values",
        nargs="*",
        type=float,
        default=[],
        help="Explicit list of lambda values (overrides grid)",
    )

    # Initial conditions
    ic = parser.add_argument_group("Initial conditions")
    ic.add_argument(
        "--phi0-Mp",
        type=float,
        default=15.0,
        help="Initial field value phi_0 in units of Mp (default: 15.0)",
    )
    ic.add_argument(
        "--pi0-Mp",
        type=float,
        default=0.0,
        help="Initial field velocity pi_0 = dphi/dN in units of Mp "
        "(default: 0.0, i.e. start at rest)",
    )

    # Instanton parameters
    inst = parser.add_argument_group("Instanton parameters")
    inst.add_argument(
        "--N-init-low",
        type=float,
        default=20.0,
        help="Lower bound of N_init grid: e-folds before end of "
        "inflation at instanton start (default: 20.0)",
    )
    inst.add_argument(
        "--N-init-high",
        type=float,
        default=20.0,
        help="Upper bound of N_init grid (default: 20.0)",
    )
    inst.add_argument(
        "--N-init-samples",
        type=int,
        default=1,
        help="Number of N_init sample points (default: 1)",
    )
    inst.add_argument(
        "--N-init-values",
        nargs="*",
        type=float,
        default=[],
        help="Explicit list of N_init values (overrides grid)",
    )
    inst.add_argument(
        "--N-final-low",
        type=float,
        default=5.0,
        help="Lower bound of N_final grid: e-folds before end of "
        "inflation at instanton end (default: 5.0)",
    )
    inst.add_argument(
        "--N-final-high",
        type=float,
        default=5.0,
        help="Upper bound of N_final grid (default: 5.0)",
    )
    inst.add_argument(
        "--N-final-samples",
        type=int,
        default=1,
        help="Number of N_final sample points (default: 1)",
    )
    inst.add_argument(
        "--N-final-values",
        nargs="*",
        type=float,
        default=[],
        help="Explicit list of N_final values (overrides grid)",
    )
    inst.add_argument(
        "--delta-Nstar-low",
        type=float,
        default=0.1,
        help="Lower bound of delta_Nstar grid (default: 0.1)",
    )
    inst.add_argument(
        "--delta-Nstar-high",
        type=float,
        default=3.0,
        help="Upper bound of delta_Nstar grid (default: 3.0)",
    )
    inst.add_argument(
        "--delta-Nstar-samples",
        type=int,
        default=10,
        help="Number of delta_Nstar sample points (default: 10)",
    )
    inst.add_argument(
        "--delta-Nstar-values",
        nargs="*",
        type=float,
        default=[],
        help="Explicit list of delta_Nstar values (overrides grid)",
    )

    # Output sampling
    samp = parser.add_argument_group("Output sampling")
    samp.add_argument(
        "--samples-per-N",
        type=float,
        default=25.0,
        help="Sampling density: number of trajectory sample "
        "points per e-fold (default: 25.0)",
    )

    # Actions
    act = parser.add_argument_group("Actions")
    act.add_argument(
        "--inventory",
        action="store_true",
        default=False,
        help="Print database inventory and exit",
    )
    act.add_argument(
        "--show-all",
        action="store_true",
        default=False,
        help="Show all items in inventory (not just first/last 10)",
    )

    return parser
