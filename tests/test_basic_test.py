# pylint: skip-file
# fmt: off
# flake8: noqa

"""Basic Test"""

import pytest
from dotenv import load_dotenv
from pytango_client_wrapper import PyTangoClientWrapper

load_dotenv()  # Load environment variables from .env file

# logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
# _logger = logging.getLogger(__name__)

@pytest.mark.nightly
@pytest.mark.all
class TestBasic():

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
