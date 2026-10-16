"""
Session-level test fixtures.

- _fresh_db: drops and recreates all tables once per session so every test run starts
  from a known-clean state (avoids phone-number conflicts on repeated runs).
- _disable_rate_limiters: disables ALL three Limiter instances (main + each router's
  own local instance) for the duration of each test. The @limiter.limit() decorator
  in slowapi checks `self.enabled` on the LOCAL Limiter, not app.state.limiter, so
  we must disable all of them to prevent inter-test rate-limit bleed.
"""
import pytest

from app.db.base import Base, engine
from app.main import app
from app.routers.donations import limiter as donations_limiter
from app.routers.receipts import limiter as receipts_limiter
from scripts.seed import run as seed_run


@pytest.fixture(scope="session", autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_run()
    yield


@pytest.fixture(autouse=True)
def _disable_rate_limiters():
    """Disable rate limiting for each test to prevent cross-test counter bleed."""
    all_limiters = [app.state.limiter, donations_limiter, receipts_limiter]
    for lim in all_limiters:
        lim.enabled = False
    yield
    for lim in all_limiters:
        lim.enabled = True