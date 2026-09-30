"""Generates a deliberately messy demo dataset (run once)."""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 1500

age = rng.normal(38, 11, n).clip(18, 80).round()
income = (age * 900 + rng.lognormal(10, 0.6, n)).round(2)
tenure = rng.integers(0, 120, n)
spend = (income * 0.02 + rng.normal(0, 50, n)).round(2)

df = pd.DataFrame(
    {
        "customer_id": range(1000, 1000 + n),
        "age": age,
        "income": income,
        "tenure_months": tenure,
        "monthly_spend": spend,
        "spend_thousands": (spend / 1000).round(5),  # perfectly correlated with monthly_spend
        "city": rng.choice(["Pune", "Mumbai", "Delhi", "Bengaluru", "Chennai"], n),
        "plan": rng.choice(["basic", "standard", "premium"], n, p=[0.6, 0.3, 0.1]),
        "postal_code": rng.integers(411001, 411060, n).astype(str),  # numeric stored as text
        "country": "India",  # constant
        "notes": np.nan,  # empty
        "churn": (rng.random(n) < 1 / (1 + np.exp((tenure - 40) / 15))).astype(int),
    }
)
df.loc[rng.choice(n, 120, replace=False), "age"] = np.nan
df.loc[rng.choice(n, 700, replace=False), "monthly_spend"] = np.nan
df.loc[rng.choice(n, 12, replace=False), "income"] *= 25  # extreme outliers
df = pd.concat([df, df.sample(25, random_state=1)], ignore_index=True)  # duplicate rows

out = Path(__file__).parent / "customers_messy.csv"
df.to_csv(out, index=False)
print(f"Wrote {out} ({len(df)} rows)")