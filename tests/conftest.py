# pylint: skip-file
# fmt: off
# flake8: noqa

import logging
import os
import os.path
from typing import List

import pytest
from connection_utils import DeviceKey, create_proxy, get_fqdn
from dotenv import load_dotenv

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
def logger() -> logging.Logger:
    return logging.getLogger(__name__)


@pytest.fixture(scope="session")
def all_test_ids_for_scenario() -> List[str]:
    return []


@pytest.fixture(scope="session")
def namespace(request) -> str:
    namespace_value = request.config.option.namespace
    if namespace_value is None:
        pytest.skip()
    return namespace_value


@pytest.fixture(scope="session")
def cluster_domain(request) -> str:
    return request.config.getoption("--cluster_domain")


@pytest.fixture(scope="session")
def emulator_base_url(namespace: str, cluster_domain: str) -> str:
    return f"{namespace}.svc.{cluster_domain}:5001"


@pytest.fixture(scope="function")
def emulator_url(device_idx: int, emulator_base_url: str) -> str:
    return f"fhs-vcc-emulator-{device_idx}.{emulator_base_url}"


@pytest.fixture(scope="session")
def tango_host(request) -> str:
    return request.config.getoption("--tango_host")


@pytest.fixture(scope="session")
def test_id(request) -> str:
    return request.config.getoption("--test_id")


@pytest.fixture(scope="session")
def results_dir() -> str:
    current_dir = os.getcwd()
    results_dir = current_dir + "/results"
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


@pytest.fixture(scope="function")
def all_bands_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.ALL_BANDS)


@pytest.fixture(scope="function")
def eth_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.ETHERNET)


@pytest.fixture(scope="function")
def pv_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.PACKET_VALIDATION)


@pytest.fixture(scope="function")
def wib_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.WIDEBAND_INPUT_BUFFER)


@pytest.fixture(scope="function")
def wfs_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.WIDEBAND_FREQ_SHIFTER)


@pytest.fixture(scope="function")
def vcc_123_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.VCC_123)


@pytest.fixture(scope="function")
def fss_fqdn(device_idx: int) -> str:
    return get_fqdn(device_idx, DeviceKey.FREQ_SLICE_SELECTION)


@pytest.fixture(scope="function")
def all_bands_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.ALL_BANDS)


@pytest.fixture(scope="function")
def eth_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.ETHERNET)


@pytest.fixture(scope="function")
def pv_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.PACKET_VALIDATION)


@pytest.fixture(scope="function")
def wib_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.WIDEBAND_INPUT_BUFFER)


@pytest.fixture(scope="function")
def wfs_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.WIDEBAND_FREQ_SHIFTER)


@pytest.fixture(scope="function")
def vcc_123_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.VCC_123)


@pytest.fixture(scope="function")
def fss_proxy(device_idx: int) -> str:
    return create_proxy(device_idx, DeviceKey.FREQ_SLICE_SELECTION)


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
