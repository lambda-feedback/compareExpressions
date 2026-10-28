import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: excluded from the deployed healthcheck (see evaluation_tests.py)")
