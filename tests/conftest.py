import pytest
from ulpf.store import Store

@pytest.fixture
def store(tmp_path):
    value=Store(tmp_path)
    yield value
    value.close()

@pytest.fixture
def source(store): return store.register_source("Test device",mode="replay")
