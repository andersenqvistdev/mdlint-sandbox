"""Harness smoke test — proves the package imports and CI is wired.

Replaced by real tests as rules land (see .company/vision.md G1-G9).
"""

import mdlint


def test_package_imports():
    assert mdlint.__version__
