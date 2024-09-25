"""Basic Test"""
import logging

import pytest
from dotenv import load_dotenv
# from lib import get_parameters, powerswitch, utils
# from lib.constant import LOG_FORMAT
from pytest_bdd import given, scenario, then, when

load_dotenv()  # Load environment variables from .env file

# logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
_logger = logging.getLogger(__name__)

a = 0

@pytest.mark.nightly
@pytest.mark.all
@scenario("features/basic_test.feature", "FHS Basic Test")
def test_basic_test():
    """Basic Test."""


@given("that the precondition exists")
def precondition_exists():
    a = 1


@when("something happens")
def something_happens():
    a += 1


@then("the test works")
def test_works():
    assert a == 2
