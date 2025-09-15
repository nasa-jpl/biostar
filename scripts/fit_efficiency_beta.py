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
        return (q1 - perc_1["x"]) ** 2 + (q2 - perc_2["x"]) ** 2

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
    alpha, beta = fit_beta(
        mean / pour, {"p": lower_p, "x": lower_x / pour}, {"p": upper_p, "x": upper_x / pour}
    )
    print([alpha, beta])
    print(
        f"{alpha / (alpha + beta)} ({beta_dist.ppf(lower_p, alpha, beta)}, {beta_dist.ppf(upper_p, alpha, beta)})"
    )
