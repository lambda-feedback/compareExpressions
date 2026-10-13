"""
    The base image's healthcheck loads `TestPreviewFunction` from this module.
    The preview tests are run as part of the pytest suite in `evaluation_tests.py`.
"""
import unittest


class TestPreviewFunction(unittest.TestCase):
    pass
