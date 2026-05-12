import pytest
import jdkman.registry as registry


@pytest.fixture(autouse=True)
def reset_registry_cache():
    # noinspection PyProtectedMember
    registry._managed_cache.clear()
    yield
    # noinspection PyProtectedMember
    registry._managed_cache.clear()

