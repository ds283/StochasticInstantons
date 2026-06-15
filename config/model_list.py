# config/model_list.py
from InflationConcepts import QuadraticPotential, QuarticPotential


def build_model_list(pool, units, args):
    """
    Return a list of model descriptor dicts, one per potential configuration.
    Each dict has keys:
        "label":     str — human-readable label for log output
        "potential": AbstractPotential — persisted potential object
    The pool.object_get() calls here ensure the potential parameters are
    registered in the database before the pipeline begins.
    """
    import ray
    import numpy as np

    models = []

    if args.potential_type == "Quadratic":
        if len(args.m_values_Mp) > 0:
            m_sample = sorted(args.m_values_Mp)
        else:
            n = max(1, round(
                args.samples_per_log10_m
                * (args.log10_m_high_Mp - args.log10_m_low_Mp) + 0.5
            ))
            m_sample = sorted(
                np.logspace(args.log10_m_low_Mp, args.log10_m_high_Mp,
                            n, endpoint=True).tolist()
            )

        m_objects = ray.get(
            pool.object_get(
                "inflaton_mass",
                payload_data=[
                    {"value": m * units.PlanckMass, "units": units}
                    for m in m_sample
                ],
            )
        )

        pot_objects = ray.get(
            pool.object_get(
                "QuadraticPotential",
                payload_data=[{"m": m, "units": units} for m in m_objects],
            )
        )

        for m_val, pot in zip(m_sample, pot_objects):
            models.append({
                "label": f"Quadratic(m={m_val:.4g} Mp)",
                "potential": pot,
            })

    elif args.potential_type == "Quartic":
        if len(args.lambda_values) > 0:
            lambda_sample = sorted(args.lambda_values)
        else:
            n = max(1, round(
                args.samples_per_log10_lambda
                * (args.log10_lambda_high - args.log10_lambda_low) + 0.5
            ))
            lambda_sample = sorted(
                np.logspace(args.log10_lambda_low, args.log10_lambda_high,
                            n, endpoint=True).tolist()
            )

        lambda_objects = ray.get(
            pool.object_get(
                "quartic_coupling",
                payload_data=[{"value": lm} for lm in lambda_sample],
            )
        )

        pot_objects = ray.get(
            pool.object_get(
                "QuarticPotential",
                payload_data=[
                    {"lambda_": lm, "units": units} for lm in lambda_objects
                ],
            )
        )

        for lm_val, pot in zip(lambda_sample, pot_objects):
            models.append({
                "label": f"Quartic(lambda={lm_val:.4g})",
                "potential": pot,
            })

    else:
        raise ValueError(f"Unknown potential type: {args.potential_type!r}")

    return models
