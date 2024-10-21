# pylint: skip-file
# fmt: off
# flake8: noqa

import logging
import os
import os.path
from typing import List

import pytest
from dotenv import load_dotenv
from proxy_utils import create_proxy, get_fqdn

load_dotenv()  # Load environment variables from .env file


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
def logger():
    return logging.getLogger(__name__)


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


@pytest.fixture(scope="function")
def all_bands_fqdn(device_idx):
    return get_fqdn(device_idx, "all_bands")


@pytest.fixture(scope="function")
def eth_fqdn(device_idx):
    return get_fqdn(device_idx, "ethernet")


@pytest.fixture(scope="function")
def pv_fqdn(device_idx):
    return get_fqdn(device_idx, "pv")


@pytest.fixture(scope="function")
def wib_fqdn(device_idx):
    return get_fqdn(device_idx, "wib")


@pytest.fixture(scope="function")
def wfs_fqdn(device_idx):
    return get_fqdn(device_idx, "wfs")


@pytest.fixture(scope="function")
def vcc_123_fqdn(device_idx):
    return get_fqdn(device_idx, "vcc_123")


@pytest.fixture(scope="function")
def fss_fqdn(device_idx):
    return get_fqdn(device_idx, "fss")


@pytest.fixture(scope="function")
def all_bands_proxy(device_idx):
    return create_proxy(device_idx, "all_bands")


@pytest.fixture(scope="function")
def eth_proxy(device_idx):
    return create_proxy(device_idx, "ethernet")


@pytest.fixture(scope="function")
def pv_proxy(device_idx):
    return create_proxy(device_idx, "pv")


@pytest.fixture(scope="function")
def wib_proxy(device_idx):
    return create_proxy(device_idx, "wib")


@pytest.fixture(scope="function")
def wfs_proxy(device_idx):
    return create_proxy(device_idx, "wfs")


@pytest.fixture(scope="function")
def vcc_123_proxy(device_idx):
    return create_proxy(device_idx, "vcc_123")


@pytest.fixture(scope="function")
def fss_proxy(device_idx):
    return create_proxy(device_idx, "fss")


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


# note that if sessionstart fails this step will not be executed
def pytest_sessionfinish():
    pass
