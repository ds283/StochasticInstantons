import argparse

import configargparse

from config.defaults import DEFAULT_ABS_TOLERANCE, DEFAULT_REL_TOLERANCE

DEFAULT_LABEL = "ChamPBH-test"
DEFAULT_TIMEOUT = 60
DEFAULT_SHARDS = 20
DEFAULT_RAY_ADDRESS = "auto"

DEFAULT_Z_END = 0.1
DEFAULT_T_INIT_GEV = 20000

DEFAULT_LOG10_ONE_PLUS_Z_HIGH = 35
DEFAULT_LOG10_ONE_PLUS_Z_LOW = 0
DEFAULT_SAMPLES_PER_LOG10_Z = 250

DEFAULT_BETA_LOW = 0.1
DEFAULT_BETA_HIGH = 3.0
DEFAULT_SAMPLES_PER_BETA = 5

DEFAULT_LOG10_M_LOW_EV = 25
DEFAULT_LOG10_M_HIGH_EV = 26.5
DEFAULT_SAMPLES_PER_LOG10_M_EV = 6

DEFAULT_LOG10_LAMBDA_LOW_EV = -2
DEFAULT_LOG10_LAMBDA_HIGH_EV = 1
DEFAULT_SAMPLES_PER_LOG10_LAMBDA_EV = 6

allowed_drop_actions = ["scalar-model", "adiabatic-history", "bbn-data"]
potential_types = ["Exponential", "InversePower", "Starobinsky", "Recliner"]


def create_argument_parser() -> configargparse.ArgumentParser:
    parser = configargparse.ArgumentParser(
        config_file_parser_class=configargparse.YAMLConfigFileParser
    )

    parser.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        help="read options from the specified configuration file",
    )
    parser.add_argument(
        "--database",
        required=True,
        type=str,
        default=None,
        help="read/write work items using the specified database cache",
    )
    parser.add_argument(
        "--inventory",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="show an inventory of the datastore content",
    )
    parser.add_argument(
        "--show-all",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="do not truncate long lists of inventory items",
    )
    parser.add_argument(
        "--job-name",
        default=DEFAULT_LABEL,
        help="specify a label for this job (used to identify integrations and other numerical products)",
    )
    parser.add_argument(
        "--shards",
        type=int,
        default=DEFAULT_SHARDS,
        help="specify number of shards to be used when creating a new datastore (if used)",
    )
    parser.add_argument(
        "--db-timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="specify connection timeout for database layer",
    )
    parser.add_argument(
        "--profile-db",
        type=str,
        default=None,
        help="write profiling and performance data to the specified database",
    )
    parser.add_argument(
        "--potential-type",
        type=str,
        choices=potential_types,
        help="specify potential type to use",
    )
    parser.add_argument(
        "--samples-log10-z",
        type=int,
        default=DEFAULT_SAMPLES_PER_LOG10_Z,
        help="specify number of z-sample points per log10(z)",
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=DEFAULT_ABS_TOLERANCE,
        help="specify absolute tolerance used during integration",
    )
    parser.add_argument(
        "--rel-tol",
        type=float,
        default=DEFAULT_REL_TOLERANCE,
        help="specify relative tolerance used during integration",
    )
    parser.add_argument(
        "--T-init-GeV",
        type=float,
        default=DEFAULT_T_INIT_GEV,
        help="set initial temperature in Jordan frame, specified in GeV",
    )
    parser.add_argument(
        "--T-stop-GeV",
        type=float,
        default=None,
        help="set stopping temperature in Jordan frame, specified in GeV",
    )
    parser.add_argument(
        "--beta-low",
        type=float,
        default=DEFAULT_BETA_LOW,
        help="minimum value of beta to sample",
    )
    parser.add_argument(
        "--beta-high",
        type=float,
        default=DEFAULT_BETA_HIGH,
        help="maximum value of beta to sample",
    )
    parser.add_argument(
        "--samples-per-beta",
        type=int,
        default=DEFAULT_SAMPLES_PER_BETA,
        help="number of samples per beta",
    )
    parser.add_argument(
        "--beta-values",
        type=float,
        nargs="*",
        action="extend",
        default=[],
        help="specify one or more beta values to sample",
    )
    parser.add_argument(
        "--log10-M-low-eV",
        type=float,
        default=DEFAULT_LOG10_M_LOW_EV,
        help="minimum value of log10(M/eV) to sample",
    )
    parser.add_argument(
        "--log10-M-high-eV",
        type=float,
        default=DEFAULT_LOG10_M_HIGH_EV,
        help="maximum value of log10(M/eV) to sample",
    )
    parser.add_argument(
        "--samples-per-log10-M-eV",
        type=int,
        default=DEFAULT_SAMPLES_PER_LOG10_M_EV,
        help="number of samples per log10(M/eV)",
    )
    parser.add_argument(
        "--M-values-eV",
        type=float,
        nargs="*",
        action="extend",
        default=[],
        help="specify one or more values of M/eV to sample",
    )
    parser.add_argument(
        "--M-values-Mp",
        type=float,
        nargs="*",
        action="extend",
        default=[],
        help="specify one or more values of M/Mp to sample",
    )
    parser.add_argument(
        "--log10-Lambda-low-eV",
        type=float,
        default=DEFAULT_LOG10_LAMBDA_LOW_EV,
        help="minimum value of log10(Lambda/eV) to sample",
    )
    parser.add_argument(
        "--log10-Lambda-high-eV",
        type=float,
        default=DEFAULT_LOG10_LAMBDA_HIGH_EV,
        help="maximum value of log10(Lambda/eV) to sample",
    )
    parser.add_argument(
        "--Lambda-values-eV",
        type=float,
        nargs="*",
        action="extend",
        default=[],
        help="specify one or more values of Lambda/eV to sample",
    )
    parser.add_argument(
        "--Lambda-values-Mp",
        type=float,
        nargs="*",
        action="extend",
        default=[],
        help="specify one or more values of Lambda/Mp to sample",
    )
    parser.add_argument(
        "--log10-one-plus-z-high",
        type=float,
        default=DEFAULT_LOG10_ONE_PLUS_Z_HIGH,
        help="maximum value of log10(1+z) to sample",
    )
    parser.add_argument(
        "--log10-one-plus-z-low",
        type=float,
        default=DEFAULT_LOG10_ONE_PLUS_Z_LOW,
        help="minimum value of log10(1+z) to sample",
    )
    parser.add_argument(
        "--samples-per-log10-Lambda-eV",
        type=int,
        default=DEFAULT_SAMPLES_PER_LOG10_LAMBDA_EV,
        help="number of samples per log10(Lambda/eV)",
    )
    parser.add_argument(
        "--prune-unvalidated",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="prune unvalidated data from the datastore during startup",
    )
    parser.add_argument(
        "--drop",
        type=str,
        nargs="+",
        default=[],
        choices=allowed_drop_actions,
        help="drop one or more data categories",
        action="extend",
    )
    parser.add_argument(
        "--output",
        default="data-out",
        type=str,
        help="specify folder for output files",
    )
    parser.add_argument(
        "--Li7-axis-limits",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="limit the y-axis on Li7 plots to near the observationally-allowed region",
    )
    parser.add_argument(
        "--D-axis-limits",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="limit the y-axis on D/H plots to near the observationally-allowed region",
    )
    parser.add_argument(
        "--Yp-axis-limits",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="limit the y-axis on Y_p plots to near the observationally-allowed region",
    )
    parser.add_argument(
        "--ray-address",
        default=DEFAULT_RAY_ADDRESS,
        type=str,
        help="specify address of Ray cluster",
    )

    return parser
