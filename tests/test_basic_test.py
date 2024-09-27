# pylint: skip-file
# fmt: off
# flake8: noqa

"""Basic Test"""

import pytest
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
# _logger = logging.getLogger(__name__)

@pytest.mark.nightly
@pytest.mark.all
def test_basic_test():
    """Basic Test."""
    assert 1 + 1 == 2
