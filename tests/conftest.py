# pylint: skip-file
# fmt: off
# flake8: noqa

import logging
import os
import os.path
from typing import List

import pytest
import pytest_html
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


def pytest_configure(config):
    pytest.test_marker = config.getoption("-m")


def pytest_html_report_title(report):
    report.title = f"FHS System Test Results [tag: {pytest.test_marker}]"


# TODO: Uncomment and use this in reporting performance/metrics
#@pytest.hookimpl(hookwrapper=True)
#def pytest_runtest_makereport(item, call):
#    outcome = yield
#    report = outcome.get_result()
#    extras = getattr(report, "extras", [])
#    extras.append(pytest_html.extras.html(f"<div>Performance results go here?</div>"))
#    report.extras = extras


@pytest.fixture(scope="session")
def logger() -> logging.Logger:
    return logging.getLogger(__name__)


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


@pytest.fixture(scope="session")
def tango_host(request) -> str:
    return request.config.getoption("--tango_host")


def pytest_sessionstart(session):
    namespace = session.config.getoption("--namespace")
    tango_host = session.config.getoption("--tango_host")
    cluster_domain = session.config.getoption("--cluster_domain")

    tango_hostname = tango_host.split(":")[0]
    tango_port = tango_host.split(":")[1]

    os.environ[
        "TANGO_HOST"
    ] = f"{tango_hostname}.{namespace}.svc.{cluster_domain}:{tango_port}"
