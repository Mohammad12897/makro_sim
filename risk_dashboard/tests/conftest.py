#tests/conftest.py
import pytest
from core.utils import load_presets


@pytest.fixture
def presets():
    return load_presets()
