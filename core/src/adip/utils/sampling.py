import pandas as pd


def sample_frame(df: pd.DataFrame, max_rows: int, seed: int = 42) -> pd.DataFrame:
    """Return df unchanged if small enough, otherwise a reproducible random sample."""
    if len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=seed)