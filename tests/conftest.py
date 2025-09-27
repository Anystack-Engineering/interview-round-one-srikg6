import json
import os
import pytest


@pytest.fixture(scope="session")
def load_json_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "orders.json")
    try:
        with open(path) as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        pytest.fail(f"Could not find {path}. Error: {e}")
