"""
    Entry point for the `healthcheck` command of the deployed function.

    The base image's healthcheck loads `TestEvaluationFunction` from this module
    with `unittest`, so this wraps a run of the pytest suite in this directory
    (`*_test.py` and `tests/`). Tests marked `@pytest.mark.slow` are left out so
    the healthcheck stays within the request timeout; CI runs them all. pytest
    doesn't collect `*_tests.py`, so this module isn't picked up by that run.
"""
import os
import unittest

import pytest


class TestEvaluationFunction(unittest.TestCase):

    def test_pytest_suite(self):
        # The Lambda filesystem is read-only, so pytest's cache is disabled
        exit_code = pytest.main([os.path.dirname(os.path.abspath(__file__)), "-q", "-m", "not slow", "-p", "no:cacheprovider"])
        self.assertEqual(exit_code, pytest.ExitCode.OK)
