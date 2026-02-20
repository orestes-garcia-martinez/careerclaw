import json
from pathlib import Path
import pytest

# Path to tests/fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Exposes the fixtures directory in case a test needs direct file access.
    """
    return FIXTURES_DIR


@pytest.fixture
def load_text(fixtures_dir):
    """
    Fixture that returns a function: load_text("file.ext") -> str
    This avoids repeating file reading logic in every test file.
    """
    def _load(name: str) -> str:
        return (fixtures_dir / name).read_text(encoding="utf-8")
    return _load


@pytest.fixture
def load_json(load_text):
    """
    Fixture that returns a function: load_json("file.json") -> dict
    Built on load_text so there's one source of truth for file IO.
    """
    def _load(name: str) -> dict:
        return json.loads(load_text(name))
    return _load
