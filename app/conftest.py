def pytest_configure(config):
    config.addinivalue_line("markers", "slow: excluded from the deployed healthcheck (see evaluation_tests.py)")
