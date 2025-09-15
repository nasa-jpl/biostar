import json
import os

import numpy as np
import pandas as pd

from biostar.modules.data import PKG_DIR


def load_posterior_samples_excel(file_name: str, n_levels: int) -> dict[str, np.ndarray]:
    """Create a mapping of components to posterior samples"""

    posterior_dict = {}
    for i in range(1, n_levels + 1):
        df_post = pd.read_excel(
            os.path.join(PKG_DIR, f"data/{file_name}"),
            sheet_name=f"Level {i} Sampling",
            engine="openpyxl",
        )
        lambda_cols = [col for col in list(df_post.columns) if col.endswith(" ,lambda")]
        for col in lambda_cols:
            col_id = col[:-8]
            posterior_dict[col_id] = df_post[col].values

    return posterior_dict


def thin_posterior(posterior_dict):
    """"""

    for k in posterior_dict.keys():
        posterior_dict[k] = np.random.choice(posterior_dict[k], size=10000, replace=False).tolist()

    return posterior_dict


if __name__ == "__main__":
    fname = input("Excel File Name: ")
    n_levels = int(input("Number Levels: "))
    posterior_dict = thin_posterior(load_posterior_samples_excel(fname, n_levels))
    with open(f"biostar/data/{fname.split('.')[0] + '.json'}", "w") as f:
        json.dump(posterior_dict, f)
