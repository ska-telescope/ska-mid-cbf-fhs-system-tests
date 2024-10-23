"""Basic Test"""

from logging import Logger

import pytest
from pytango_client_wrapper import PyTangoClientWrapper


@pytest.mark.nightly
class TestBasic:
    """Basic tests."""

    @pytest.fixture(scope="class")
    def device_idx(self) -> int:
        return 1

    def test_basic_test(self):
        """Basic Test."""
        assert 1 + 1 == 2

    def test_tango(self, logger: Logger, eth_proxy: PyTangoClientWrapper, device_idx: int):
        """Basic Tango Test."""
        x = eth_proxy.read_attribute("adminMode")
        logger.debug(f"basic test: x={x}")
        assert x is not None
