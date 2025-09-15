# Optimization Details

Simple numerical optimization to fit `alpha` and `beta` parameters from known mean, lower, and upper percentiles. Can optimize for just `alpha` since the known mean allows us to derive the `beta` parameter. Optimize `alpha` to minimize squared error of the two known percentiles.

Python script used to fit beta:

```
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import beta as beta_dist


def fit_beta(mean, perc_1, perc_2):
    """"""

    def objective(alpha):
        beta = alpha * (1 - mean) / mean
        if alpha <= 0 or beta <= 0:
            return np.inf
        q1 = beta_dist.ppf(perc_1["p"], alpha, beta)
        q2 = beta_dist.ppf(perc_2["p"], alpha, beta)
        return (q1 - perc_1["x"])**2 + (q2 - perc_2["x"])**2

    res = minimize_scalar(objective, bounds=(0.01, 200), method="bounded")
    alpha_hat = res.x
    beta_hat = alpha_hat * (1 - mean) / mean

    return alpha_hat, beta_hat


if __name__ == "__main__":
    pour = float(input("Pour fraction: "))
    mean = float(input("Mean efficiency % (before adjustment): "))
    lower_p = 0.025
    lower_x = float(input("Lower percentile efficiency % (before adjustment): "))
    upper_p = 0.975
    upper_x = float(input("Upper percentile efficiency % (before adjustment): "))
    alpha, beta = fit_beta(mean / pour, {"p": lower_p, "x": lower_x / pour}, {"p": upper_p, "x": upper_x / pour})
    print([alpha, beta])
    print(f"{alpha / (alpha + beta)} ({beta_dist.ppf(lower_p, alpha, beta)}, {beta_dist.ppf(upper_p, alpha, beta)})")
```

# Efficiencies in the Paper & Pour Fraction Adjustment

The recovery efficiency paper provides some characterizations of distributions expected for a few device + device type + processing technique cases. The script above can fit beta distributions to each of these characterizations (two percentiles and a mean).

The script automatically scales the efficiency inputs by the provided pour fraction to create a "pour-fraction agnostic" distribution. The pour fraction adjustment used for each calculation is provided as a bullet under each case:

```
A Puritan cotton swab NASA standard w/ Membrane Filtration filter NASA 31% (26%, 36%)
    - Pour fraction = 0.92
B Puritan cotton swab NASA standard ESA 25% (19%, 31%)
    - Pour fraction = 0.8
C Nylon-flocked swab NASA standard ESA 23% (12%, 36%)
    - Pour fraction = 0.8
D Nylon-flocked swab ESA standard ESA 38% (32%, 45%)
    - Pour fraction = 0.8
E Copan cotton swab NASA standard ESA 10% (8%, 13%)
    - Pour fraction = 0.8
F Copan Polyester swab ESA standard ESA 10% (3%, 18%)
    - Pour fraction = 0.8
G TX3211 wipe NASA standard w/ Membrane Filtration filter NASA 27% (6%, 56%)
    - Pour fraction = 0.969
H TX3224 wipe NASA standard w/ Membrane Filtration filter NASA 12% (9%, 16%)
    - Pour fraction = 0.933
```

# Results

Below are the configurations for each possible combination of sampling device, device type, and processing technique. If `params` is a list of two numbers then it is assumed to be the output `[alpha, beta]` of the script using one of the cases from the recovery efficiency paper above. If `params` is a string then it is simply a reference to one of the cases from the paper, and the corresponding recovery efficiency distribution will be used.

```
EFFICIENCY_CONFIG = {
    "Swab;Puritan Cotton;NASA Standard": {
        "params": [45.56431672969219, 100.24149680532281],
        "default_fraction": 0.8,
    },
    "Swab;Puritan Cotton;NASA Standard (w/ Membrane Filtration)": {
        "params": [97.55218540553831, 191.9575261205754],
        "default_fraction": 0.92,
    },
    "Swab;Puritan Cotton;ESA Standard": {
        "params": "Swab;Puritan Cotton;NASA Standard",
        "default_fraction": 0.8,
    },
    "Swab;Puritan Cotton;ESA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Puritan Cotton;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.92,
    },
    "Swab;Nylon-flocked;NASA Standard": {
        "params": [9.579630660559655, 23.74082381095219],
        "default_fraction": 0.8,
    },
    "Swab;Nylon-flocked;NASA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Nylon-flocked;NASA Standard",
        "default_fraction": 0.92,
    },
    "Swab;Nylon-flocked;ESA Standard": {
        "params": [68.16498856079723, 75.34025051456537],
        "default_fraction": 0.8,
    },
    "Swab;Nylon-flocked;ESA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Nylon-flocked;ESA Standard",
        "default_fraction": 0.92,
    },
    "Swab;Copan Polyester;NASA Standard": {
        "params": "Swab;Copan Polyester;ESA Standard",
        "default_fraction": 0.8,
    },
    "Swab;Copan Polyester;NASA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Copan Polyester;ESA Standard",
        "default_fraction": 0.92,
    },
    "Swab;Copan Polyester;ESA Standard": {
        "params": [6.052080310455172, 42.3645621731862],
        "default_fraction": 0.8,
    },
    "Swab;Copan Polyester;ESA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Copan Polyester;ESA Standard",
        "default_fraction": 0.92,
    },
    "Swab;Copan Cotton;NASA Standard": {
        "params": [51.836071542660086, 362.8525007986206],
        "default_fraction": 0.8,
    },
    "Swab;Copan Cotton;NASA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Copan Cotton;NASA Standard",
        "default_fraction": 0.92,
    },
    "Swab;Copan Cotton;ESA Standard": {
        "params": "Swab;Copan Cotton;NASA Standard",
        "default_fraction": 0.8,
    },
    "Swab;Copan Cotton;ESA Standard (w/ Membrane Filtration)": {
        "params": "Swab;Copan Cotton;NASA Standard",
        "default_fraction": 0.92,
    },
    "Wipe;TX3211;NASA Standard": {
        "params": "Wipe;TX3211;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.25,
    },
    "Wipe;TX3211;NASA Standard (w/ Membrane Filtration)": {
        "params": [2.755428498737132, 7.13349822450835],
        "default_fraction": 0.92,
    },
    "Wipe;TX3211;ESA Standard": {
        "params": "Wipe;TX3211;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.25,
    },
    "Wipe;TX3211;ESA Standard (w/ Membrane Filtration)": {
        "params": "Wipe;TX3211;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.92,
    },
    "Wipe;TX3224;NASA Standard": {
        "params": "Wipe;TX3224;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.25,
    },
    "Wipe;TX3224;NASA Standard (w/ Membrane Filtration)": {
        "params": [38.27721767664384, 259.32814975926203],
        "default_fraction": 0.92,
    },
    "Wipe;TX3224;ESA Standard": {
        "params": "Wipe;TX3224;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.25,
    },
    "Wipe;TX3224;ESA Standard (w/ Membrane Filtration)": {
        "params": "Wipe;TX3224;NASA Standard (w/ Membrane Filtration)",
        "default_fraction": 0.92,
    },
}
```
