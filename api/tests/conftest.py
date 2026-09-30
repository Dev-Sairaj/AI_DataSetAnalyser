import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(storage_dir=tmp_path / "jobs", max_upload_mb=5)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def csv_bytes() -> bytes:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "a": rng.normal(size=100),
            "b": rng.choice(["x", "y"], 100),
            "y": rng.integers(0, 2, 100),
        }
    )
    return df.to_csv(index=False).encode()