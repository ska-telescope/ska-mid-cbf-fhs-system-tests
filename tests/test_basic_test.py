"""Basic Test"""

import pytest
from pytango_client_wrapper import PyTangoClientWrapper


@pytest.mark.nightly
@pytest.mark.all
class TestBasic:
    """Basic tests."""

    def test_basic_test(self):
        """Basic Test."""
        assert 1 + 1 == 2

    def test_tango(self):
        """Basic Tango Test."""
        eth_proxy = PyTangoClientWrapper()
        eth_proxy.create_tango_client("fhs/mac200/000")
        x = eth_proxy.read_attribute("adminMode")
        print(x)
        assert x is not None
