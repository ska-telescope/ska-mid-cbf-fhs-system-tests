# pylint: skip-file
# fmt: off
# flake8: noqa

import logging
import os
import os.path
from typing import List

import pytest
from dotenv import load_dotenv
from pytest_bdd import given
from ska_tango_testing.integration import TangoEventTracer

load_dotenv()  # Load environment variables from .env file

_logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption("--namespace", action="store", default="default")
    parser.addoption(
        "--cluster_domain", action="store", default="cluster.local"
    )
    parser.addoption(
        "--tango_host", action="store", default="databaseds-tango-base:10000"
    )
    parser.addoption("--test_id", action="store", default="Test_1")


@pytest.fixture(scope="session")
def all_test_ids_for_scenario() -> List[str]:
    return []


@pytest.fixture(scope="session")
def namespace(request):
    namespace_value = request.config.option.namespace
    if namespace_value is None:
        pytest.skip()
    return namespace_value


@pytest.fixture(scope="session")
def cluster_domain(request):
    return request.config.getoption("--cluster_domain")


@pytest.fixture(scope="session")
def tango_host(request):
    return request.config.getoption("--tango_host")


@pytest.fixture(scope="session")
def test_id(request):
    return request.config.getoption("--test_id")


@pytest.fixture(scope="session")
def results_dir():
    current_dir = os.getcwd()
    results_dir = current_dir + "/results"
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


@pytest.fixture(scope="session")
def state_str():
    return "State"


@pytest.fixture(scope="session")
def off_state_str():
    return "OFF"


@pytest.fixture(scope="session")
def obs_state_str():
    return "ObsState"


def pytest_sessionstart(session):
    namespace = session.config.getoption("--namespace")
    tango_host = session.config.getoption("--tango_host")
    cluster_domain = session.config.getoption("--cluster_domain")

    curr_dir = os.getcwd()

    tango_hostname = tango_host.split(":")[0]
    tango_port = tango_host.split(":")[1]

    os.environ[
        "TANGO_HOST"
    ] = f"{tango_hostname}.{namespace}.svc.{cluster_domain}:{tango_port}"

    # # Need to create a specific tracer for sending the ON command, as pytest_sessionstart can not access the event_tracer fixture
    # tracer = TangoEventTracer()
    # fqdn_cbfcontroller = "mid_csp_cbf/sub_elt/controller"
    # tracer.subscribe_event(fqdn_cbfcontroller, "longRunningCommandResult")
    # tracer.subscribe_event(fqdn_cbfcontroller, "state")


def pytest_bdd_after_scenario(request, feature, scenario):
    pass
    # namespace = request.config.getoption("--namespace")
    # event_tracer = request.getfixturevalue("event_tracer")
    # tango_host = request.config.getoption("--tango_host")
    # cluster_domain = request.config.getoption("--cluster_domain")
    # _logger.info(
    #     f"pytest_bdd_after_scenario hook: cleaning up the {feature.name} BDD test"
    # )
    # _logger.info("pytest_bdd_after_scenario hook: clean-up complete.")


# note that if sessionstart fails this step will not be executed
def pytest_sessionfinish():
    pass
    # fqdn_cbfcontroller = "mid_csp_cbf/sub_elt/controller"
    # timeout_millis = 100000
    # cbfcontroller = get_parameters.create_device_proxy(
    #     fqdn_cbfcontroller, timeout_millis
    # )

    # # as part of the clean up at the end of the session we want to undo everything that was done during the ON command, including setting the AdminMode back to off
    # cbfcontroller.write_attribute("adminMode", 1)
