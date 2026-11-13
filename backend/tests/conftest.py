"""Pytest configuration and fixtures."""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
