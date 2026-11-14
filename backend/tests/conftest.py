import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Async tests run with `@pytest.mark.anyio` on asyncio; anyio ships with httpx."""
    return "asyncio"
