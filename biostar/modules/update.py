import numpy as np
from scipy import special

from biostar.modules.data import POSTERIOR_MAP, SPEC_DENSITY_MAP, get_efficiency_params
from biostar.modules.parsing import sample_eff_tag


def likelihoods(
    lambda_samples: np.ndarray, data: np.ndarray, log: bool = False, joint: bool = True
) -> np.ndarray:
    """Calculate the likelihood of data given some value for lambda"""

    rng = np.random.default_rng()

    # Calculate base exposures using area + pour fraction
    counts = data[:, 0]
    exposures = data[:, 1] * data[:, 2]

    # Incorporate recovery efficiency and construct expected rates
    efficiencies = np.array(
        [rng.beta(data[i, 3], data[i, 4], size=len(lambda_samples)) for i in range(data.shape[0])]
    )
    expected_rates = lambda_samples.reshape(-1, 1) * exposures * efficiencies.T

    log_lik = counts * np.log(expected_rates) - special.factorial(counts) - expected_rates
    if joint:
        log_lik = log_lik.sum(axis=1)
    else:
        log_lik = log_lik.T

    if log:
        return log_lik
    return np.exp(log_lik)


def generic_prior_solution(data: np.ndarray, resolution: int = 1000) -> np.ndarray:
    """Retrieve samples from lambda analytic solution when using generic Jeffry's prior"""

    rng = np.random.default_rng()
    cfu_total = data[:, 0].sum()
    exposures = data[:, 1] * data[:, 2]
    efficiencies = np.array(
        [rng.beta(data[i, 3], data[i, 4], size=resolution) for i in range(data.shape[0])]
    )
    return rng.gamma(0.5 + cfu_total, 1 / (exposures * efficiencies.T).sum(axis=1))


def update_analogy_prior(
    lambda_samples: np.ndarray | None, data: np.ndarray, resolution: int = 1000
) -> np.ndarray:
    """Update the prior (posterior of analog component) given user provided data"""

    # Handle generic analogy case (use analytic solution from jeffry's prior)
    if lambda_samples is None:
        return generic_prior_solution(data, resolution)

    # Get resampling weights
    lik = likelihoods(lambda_samples, data, log=False, joint=True)
    weights = lik / np.sum(lik)

    # Resample from prior (replacement only if PSIS used)
    resample_idx = np.random.default_rng().choice(
        len(lambda_samples), size=resolution, replace=True, p=weights
    )

    return lambda_samples[resample_idx]


def sim_cfu(lambda_samples: np.ndarray, total_exposure: int | float) -> np.ndarray:
    """Sample a distribution of CFUs given a distribution of rates and a total exposure"""

    rng = np.random.default_rng()
    scaled_rates = lambda_samples * total_exposure
    return rng.poisson(scaled_rates)


def sim_component(
    hw: dict, samples_list: list[dict], current_sims: dict, n_sims: int = 1000
) -> np.ndarray:
    """Simulate bioburden density given a component and samples"""

    rng = np.random.default_rng()

    exposure = hw["area"] if hw["dim"].startswith("2") else hw["volume"]
    area_vol_attr = "Sampled Area" if hw["dim"].startswith("2") else "Sampled Volume"

    # For spec components we can just report the selected values
    if hw["type"] == "Unsampled - Spec":
        return {
            "mode": "spec",
            "link": None,
            "lambda": SPEC_DENSITY_MAP[hw["dim"]][hw["spec"]],
            "cfu": SPEC_DENSITY_MAP[hw["dim"]][hw["spec"]] * exposure,
        }

    # For implied components apply existing bioburden density distribution to new component exposure
    if hw["type"] == "Unsampled - Implied":
        implied_id = hw["implied_id"]
        implied_sim = current_sims["sims"][implied_id]
        return {
            "mode": "implied",
            "link": implied_id,
            "lambda": np.array(implied_sim["lambda"]),
            "cfu": sim_cfu(np.array(implied_sim["lambda"]), exposure),
        }

    # Now can assume sampled component with analogy
    analogy_prior = None if hw["analogy"] == "-- Generic --" else POSTERIOR_MAP[hw["analogy"]]
    samples = [
        row
        for row in samples_list
        if (row["Hardware ID"] == hw["id"] and row["PP Accountable"].lower() == "yes")
    ]

    # If samples exist we can update the prior
    # If analogy prior will use importance resampling
    # If generic prior (jeffry's) will use analytic solution
    if samples:
        samples_data = np.array(
            [
                [
                    row["CFU"],
                    row[area_vol_attr],
                    row["Pour Fraction"],
                    get_efficiency_params(sample_eff_tag(row))[0],
                    get_efficiency_params(sample_eff_tag(row))[1],
                ]
                for row in samples
            ]
        )
        mode = "posterior"
        draws_lambda = update_analogy_prior(analogy_prior, samples_data)
        cfu = sim_cfu(draws_lambda, exposure)

    # If samples don't exist we just plot the analogy
    # Can assume non-generic prior since these cases will be filtered out
    else:
        mode = "prior"
        draws_lambda = analogy_prior[rng.choice(len(analogy_prior), size=n_sims, replace=False)]
        cfu = sim_cfu(draws_lambda, exposure)

    return {
        "mode": mode,
        "link": hw["analogy"],
        "lambda": draws_lambda,
        "cfu": cfu,
    }
