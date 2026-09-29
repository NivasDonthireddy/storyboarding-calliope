from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import calliope

MINI_SRC = Path(__file__).resolve().parents[1] / "src"
assert Path(calliope.__file__).resolve().is_relative_to(MINI_SRC), (
    f"Tests must import the playground, not production: {calliope.__file__}"
)

from calliope.config import Settings  # noqa: E402
from calliope.main import create_app  # noqa: E402

REAL_CLIENT, REAL_SEND = httpx.AsyncClient, httpx.AsyncClient.send


@pytest.fixture(autouse=True)
def block_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Real outbound HTTP is forbidden in playground tests")

    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)


@pytest.fixture
def mock_http(monkeypatch):
    def install(handler):
        class MockClient(REAL_CLIENT):
            async def send(self, *args, **kwargs):
                assert isinstance(self._transport, httpx.MockTransport)
                return await REAL_SEND(self, *args, **kwargs)

        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda **kwargs: MockClient(
                transport=httpx.MockTransport(handler),
                **kwargs,
            ),
        )

    return install


@pytest.fixture
def settings(tmp_path):
    return Settings(offline=True, data_dir=tmp_path)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def project(client):
    response = client.post("/api/projects", json={"title": "Lantern", "idea": "Find the exit"})
    assert response.status_code == 200
    return response.json()["id"]
