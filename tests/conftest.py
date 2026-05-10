import pytest
import jdkman.registry as registry


@pytest.fixture(autouse=True)
def reset_registry_cache():
    registry._managed_cache.clear()
    yield
    registry._managed_cache.clear()
