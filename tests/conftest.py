import pytest


@pytest.fixture(autouse=True)
def isolated_memory(tmp_path, monkeypatch):
    from backend import memory
    monkeypatch.setattr(memory, "DB_PATH", tmp_path / "memory.db")
