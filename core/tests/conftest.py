import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def messy_df() -> pd.DataFrame:
    """202 rows x 7 columns with deliberately injected problems."""
    rng = np.random.default_rng(42)
    n = 200
    df = pd.DataFrame(
        {
            "id": range(n),
            "age": rng.normal(40, 8, n).round(1),
            "income": rng.normal(50_000, 8_000, n),
            "city": rng.choice(["Pune", "Mumbai", "Delhi"], n),
            "constant": ["x"] * n,
            "empty": [np.nan] * n,
            "num_as_text": [str(i) for i in range(n)],
        }
    )
    df.loc[:19, "age"] = np.nan  # 10% missing
    df.loc[0, "income"] = 5_000_000  # extreme outlier
    return pd.concat([df, df.iloc[[5, 6]]], ignore_index=True)  # 2 duplicate rows