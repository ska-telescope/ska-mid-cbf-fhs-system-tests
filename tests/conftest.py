# pylint: skip-file
# fmt: off
# flake8: noqa

import json
import logging
import os
import os.path

# import shutil
# import subprocess
# import warnings
from typing import List

import pytest
from dotenv import load_dotenv

# from lib import (
#     get_parameters,
#     param_guardrails,
#     powerswitch,
#     scan_operations,
#     utils,
# )
# from lib.constant import (
#     CBF_INPUT_JSON,
#     INIT_SYS_PARAM_JSON,
#     LOG_FORMAT,
#     TESTS_JSON,
# )
from pytest_bdd import given
from ska_tango_testing.integration import TangoEventTracer

# ska-mid-cbf-internal-schemas imports
# pylint: disable=no-name-in-module
# from test_parameters import test_parameters_validation

load_dotenv()  # Load environment variables from .env file

# logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
_logger = logging.getLogger(__name__)

# TEST_PARAMS_DIR = os.path.join(os.getcwd(), "test_parameters")

# TEST_PARAMS_DIRS = [
#     TEST_PARAMS_DIR,
#     os.path.join(TEST_PARAMS_DIR, "delay_model_package"),
#     os.path.join(TEST_PARAMS_DIR, "assign_resources"),
#     os.path.join(TEST_PARAMS_DIR, "release_resources"),
#     os.path.join(TEST_PARAMS_DIR, "configure_scan"),
#     os.path.join(TEST_PARAMS_DIR, "scan"),
#     os.path.join(TEST_PARAMS_DIR, "checkpoints"),
# ]


def pytest_addoption(parser):
    parser.addoption("--namespace", action="store", default="default")
    parser.addoption(
        "--cluster_domain", action="store", default="cluster.local"
    )
    parser.addoption(
        "--tango_host", action="store", default="databaseds-tango-base:10000"
    )
    parser.addoption("--test_id", action="store", default="Test_1")


# @pytest.fixture(scope="module")
# def fqdn_cbfcontroller() -> str:
#     return "mid_csp_cbf/sub_elt/controller"


# @pytest.fixture(scope="module")
# def fqdn_subarray() -> str:
#     return "mid_csp_cbf/sub_elt/subarray_01"


# @pytest.fixture(scope="module")
# def event_tracer(fqdn_cbfcontroller, fqdn_subarray) -> TangoEventTracer:
#     tracer = TangoEventTracer()

#     tracer.subscribe_event(fqdn_cbfcontroller, "longRunningCommandResult")
#     tracer.subscribe_event(fqdn_cbfcontroller, "adminMode")
#     tracer.subscribe_event(fqdn_cbfcontroller, "state")

#     tracer.subscribe_event(fqdn_subarray, "obsstate")
#     tracer.subscribe_event(fqdn_subarray, "longRunningCommandResult")

#     return tracer


@pytest.fixture(scope="session")
def all_test_ids_for_scenario() -> List[str]:
    return []


# @pytest.fixture(scope="session")
# def signal_chain_verification_report_generator(
#     all_test_ids_for_scenario: List[str], namespace: str, results_dir: str
# ) -> None:
#     yield
#     # Report generation is placed after the yield so it will only run after the test scenario has completed and is able to acquire data from the completed test run
#     generate_reports_for_specified_test_ids(
#         results_dir, namespace, all_test_ids_for_scenario
#     )
#     check_reports_are_generated_for_specified_test_ids(
#         results_dir, all_test_ids_for_scenario
#     )


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


# @pytest.fixture(scope="session")
# def subarray_proxy_default():
#     fqdn_subarray = "mid_csp_cbf/sub_elt/subarray_01"
#     return get_parameters.create_device_proxy(fqdn_subarray)


# @pytest.fixture(scope="session")
# def cbfcontroller_proxy():
#     fqdn_cbfcontroller = "mid_csp_cbf/sub_elt/controller"
#     timeout_millis = 100000
#     cbfcontroller_proxy = get_parameters.create_device_proxy(
#         fqdn_cbfcontroller, timeout_millis
#     )
#     cbfcontroller_proxy.write_attribute("simulationMode", 0)
#     cbfcontroller_proxy.write_attribute("adminMode", 0)
#     return cbfcontroller_proxy


# @pytest.fixture(scope="session")
# def vcc_max(cbfcontroller_proxy):
#     max_capabilities = cbfcontroller_proxy.get_property("MaxCapabilities")
#     if max_capabilities is None:
#         num_vcc = 4
#         _logger.info(
#             f"max_capabilities is None - using default vcc: {num_vcc}"
#         )
#     else:
#         num_vcc = max_capabilities["MaxCapabilities"][0].removeprefix("VCC:")
#     return num_vcc


# @pytest.fixture(scope="session")
# def fsp_max(cbfcontroller_proxy):
#     max_capabilities = cbfcontroller_proxy.get_property("MaxCapabilities")
#     if max_capabilities is None:
#         num_fsp = 4
#         _logger.info(
#             f"max_capabilities is None - using default fsp: {num_fsp}"
#         )
#     else:
#         num_fsp = max_capabilities["MaxCapabilities"][1].removeprefix("FSP:")
#     return num_fsp


# @pytest.fixture(scope="function")
# def run_parameter_guardrail_for_k_values(sys_param, test_id) -> None:
#     """Compares the k value information from the init_sys_param file and selected
#     via the system_param key to the corresponding entry in cbf_input for the test being run.

#     Uses the cbf_input and init_sys_param file referred to by lib/constant.py
#     Args:
#     - sys_param: init_sys_param key to determine which k value information to grab
#     - test_id: test key to determine which test is being used
#     """
#     with open(CBF_INPUT_JSON, "r", encoding="utf-8") as cbf_input_data_file:
#         cbf_input_dict = json.load(cbf_input_data_file)
#         cbf_input_data = cbf_input_dict["cbf_input_data"]

#     with open(TESTS_JSON, "r", encoding="utf-8") as tests_file:
#         tests_dict = json.load(tests_file)
#         tests = tests_dict["tests"]
#         cbf_in = tests[test_id]["cbf_input_data"]
#         dishid = cbf_input_data[cbf_in]["receptors"][0]["dish_id"]
#         kvaluecbf = cbf_input_data[cbf_in]["receptors"][0]["sample_rate_k"]

#     with open(
#         INIT_SYS_PARAM_JSON, "r", encoding="utf-8"
#     ) as init_sys_param_file:
#         init_sys_dict = json.load(init_sys_param_file)
#         init_sys_param = init_sys_dict["init_sys_param"][sys_param]

#     cbf_in = tests[test_id]["cbf_input_data"]
#     dishid = cbf_input_data[cbf_in]["receptors"][0]["dish_id"]
#     kvaluecbf = cbf_input_data[cbf_in]["receptors"][0]["sample_rate_k"]
#     initkval = init_sys_param["dish_parameters"][dishid]["k"]

#     assert (
#         kvaluecbf == initkval
#     ), f"The K_value is not consistent between config files.\n For dish_id: {dishid}, The k_value in cbf_input_file: {kvaluecbf}, does not match the k value for system_param: {sys_param} in init_sys_param: {initkval}.\n  "

#     _logger.info(
#         "k_value is consistent between cbf_input_data and init_sys_param config files"
#     )


# @pytest.fixture(scope="session")
# def validate_test_parameters(
#     namespace,
#     results_dir,
#     hw_config_file,
#     slim_fs_config_file,
#     slim_vis_config_file,
#     talon_list,
#     sys_param,
# ):
#     # Run validation script from the ska-mid-cbf-internal-schemas package
#     _logger.info("system-tests: validating test parameters...")
#     test_parameters_validation.validate_test_parameters(TEST_PARAMS_DIR)
#     _logger.info("system-tests: done validating test parameters!")

#     _logger.info("system-tests: generating test parameters summary...")
#     test_params_dir = os.path.join(results_dir, "test_parameters")

#     # Ensure that the contents of test_params_dir was not from a previous
#     # run of the test by deleting test_params_dir and its contents
#     shutil.rmtree(test_params_dir, ignore_errors=True)
#     os.makedirs(test_params_dir, exist_ok=False)

#     # Generate test_parameters_summary.json and test_parameters.json
#     curr_dir = os.getcwd()
#     generate_test_params_summary_str = f"cp {curr_dir}/test_parameters/tests.json {test_params_dir}/test_parameters_summary.json"
#     _logger.info(generate_test_params_summary_str)
#     generate_test_params_summary_result = subprocess.run(
#         [generate_test_params_summary_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(f"system-tests: {generate_test_params_summary_result.stdout}")

#     generate_test_params_str = f"{curr_dir}/test_parameters/test_parameters.py -t -o {test_params_dir}"
#     _logger.info(generate_test_params_str)
#     generate_test_params_result = subprocess.run(
#         [generate_test_params_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(f"system-tests: {generate_test_params_result.stdout}")

#     param_guardrails.run_parameter_guardrail_for_subarray_id(test_params_dir)

#     # copy the init_sys_param.json to the results dir
#     copy_initsysparam_str = f"cp {curr_dir}/test_parameters/init_sys_param.json {test_params_dir}/init_sys_param.json"
#     _logger.info(copy_initsysparam_str)
#     copy_initsysparam_result = subprocess.run(
#         [copy_initsysparam_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(
#         f"system-tests init_sys_param.json cp stdout: {copy_initsysparam_result.stdout}"
#     )

#     # copy the hw_config_file so it can be saved to artifacts
#     hw_config_dir = os.path.join(test_params_dir, "hw_config")
#     os.makedirs(hw_config_dir, exist_ok=False)
#     kube_cp_str = f"cp {hw_config_file} {hw_config_dir}/{os.path.basename(hw_config_file)}"
#     _logger.info(kube_cp_str)
#     cp_result = subprocess.run(
#         [kube_cp_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(f"system-tests hw_config_file cp stdout: {cp_result.stdout}")

#     # copy the slim_fs_config_file so it can be saved to artifacts
#     slim_config_dir = os.path.join(test_params_dir, "slim_config")
#     os.makedirs(slim_config_dir, exist_ok=False)
#     kube_cp_str = f"cp {slim_fs_config_file} {slim_config_dir}/{os.path.basename(slim_fs_config_file)}"
#     _logger.info(kube_cp_str)
#     cp_result = subprocess.run(
#         [kube_cp_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(
#         f"system-tests slim_fs_config_file cp stdout: {cp_result.stdout}"
#     )

#     # copy the slim_vis_config_file so it can be saved to artifacts
#     kube_cp_str = f"cp {slim_vis_config_file} {slim_config_dir}/{os.path.basename(slim_vis_config_file)}"
#     _logger.info(kube_cp_str)
#     cp_result = subprocess.run(
#         [kube_cp_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     _logger.info(
#         f"system-tests slim_vis_config_file cp stdout: {cp_result.stdout}"
#     )

#     talondx_config_dir = os.path.join(test_params_dir, "talondx_config")
#     os.makedirs(talondx_config_dir, exist_ok=False)
#     # Locate the talondx_boardmap.json file in the Engineering Console
#     kubectl_exec_str = f"kubectl exec ds-deployer-deployer-0 -n {namespace} -- find talondx_config -name 'talondx_boardmap.json'"
#     _logger.info(kubectl_exec_str)
#     kubectl_exec_result = subprocess.run(
#         [kubectl_exec_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )
#     talondx_boardmap_file = kubectl_exec_result.stdout.split("/")[-1].replace(
#         "\n", ""
#     )
#     # Copy the talondx_boardmap.json file from the Engineering Console to system-tests
#     cp_talondx_boardmap_str = f"kubectl cp {namespace}/ds-cbfcontroller-controller-0:/app/mnt/talondx_config/{os.path.basename(talondx_boardmap_file)} {talondx_config_dir}/{os.path.basename(talondx_boardmap_file)}"
#     subprocess.run(
#         [cp_talondx_boardmap_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         text=True,
#         check=False,
#     )

#     # Get OS and Kernel information for each talon board
#     hw_config = get_parameters.read_yaml_file(hw_config_file)
#     talons = get_parameters.get_talon_boards_list(talon_list)
#     for talon in talons:
#         talon_ip = get_parameters.get_talon_ip_from_hw_config(talon, hw_config)
#         get_talon_info_str = f"{curr_dir}/scripts/get_talon_board_info.sh {talon} {talon_ip} 2>&1"
#         _logger.info(get_talon_info_str)
#         subprocess.run(
#             [get_talon_info_str],
#             shell=True,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             check=False,
#         )
#     cp_talon_info_str = f"cp {curr_dir}/talon_board_info.txt {test_params_dir}/talon_board_info.txt"
#     _logger.info(cp_talon_info_str)
#     subprocess.run(
#         [cp_talon_info_str],
#         shell=True,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         text=True,
#         check=False,
#     )


# @pytest.fixture(scope="session")
# def send_test_parameters_to_cbf_tools(namespace, results_dir):
#     sv_dir = "/app"
#     copy_test_parameters_to_pod(namespace, "sv", sv_dir)

#     # sv also needs needs the test_parameters.json from results dir
#     kube_cp_str = f"kubectl cp {results_dir}/test_parameters/test_parameters.json {namespace}/sv:{sv_dir}/test_parameters/test_parameters.json"
#     _logger.info(kube_cp_str)
#     subprocess.run(
#         [kube_cp_str],
#         shell=True,
#         check=False,
#     )


# def generate_reports_for_specified_test_ids(
#     results_dir: str, namespace: str, test_ids: List[str]
# ) -> None:
#     """
#     the reports contain information for each test within the test ids.
#     this function calls a utils function that starts the report generation
#     within the sv (signal verification) container. Any old reports currently in the folder will be deleted.
#     """

#     # create folder specifically for reports and ensure it is new and empty
#     reports_dir = os.path.join(results_dir, "reports")
#     shutil.rmtree(reports_dir, ignore_errors=True)
#     os.makedirs(reports_dir, exist_ok=False)

#     # generate overall summary report
#     utils.generate_report(namespace, "report_summary", reports_dir, test_ids)

#     # generate more detailed report for each individual test
#     utils.generate_report(namespace, "test_id_report", reports_dir, test_ids)


# def check_reports_are_generated_for_specified_test_ids(
#     results_dir: str, test_ids: List[str]
# ) -> None:
#     """
#     this function checks that the summary report has been generated along with
#     an individual report for each test id.
#     """

#     report_name = os.path.join(results_dir, "reports", "report_summary.html")
#     assert os.path.isfile(report_name), f"report not found: {report_name}"

#     for test_id in test_ids:
#         report_name = os.path.join(results_dir, "reports", f"{test_id}.html")
#         assert os.path.isfile(report_name), f"report not found: {report_name}"


# def copy_test_parameters_to_pod(
#     namespace: str, pod: str, base_dir: str
# ) -> None:
#     """Copies the entire test parameters folder to a given pod and directory.

#     test_parameters directory will be spawned inside given directory. Any
#     pre-existing test_parameters directory in that location will be deleted.

#     Args:
#         namespace
#         pod: name of pod
#         base_dir: full path to directory where test params dir should spawn

#     Raises:
#         e: suprocess.CalledProcessError when check on copy fails
#     """

#     _logger.info(
#         f"Deleting then creating directory to store test parameters in {pod} pod..."
#     )

#     rmdir_test_parameters_str = f"kubectl exec {pod} -n {namespace} -- rm -rf {base_dir}/test_parameters"
#     _logger.info(rmdir_test_parameters_str)
#     subprocess.run(
#         [rmdir_test_parameters_str],
#         shell=True,
#         check=False,
#     )

#     mkdir_test_parameters_str = f"kubectl exec {pod} -n {namespace} -- mkdir {base_dir}/test_parameters"
#     _logger.info(mkdir_test_parameters_str)
#     subprocess.run(
#         [mkdir_test_parameters_str],
#         shell=True,
#         check=False,
#     )

#     _logger.info(
#         f"Copying the test parameters to {pod} pod, dir: {base_dir}..."
#     )
#     for test_param_dir in TEST_PARAMS_DIRS:
#         if test_param_dir == TEST_PARAMS_DIR:
#             dest_path = "test_parameters/tests.json"
#             cp_test_parameters_str = f"kubectl cp {test_param_dir}/tests.json {namespace}/{pod}:{base_dir}/test_parameters/tests.json"
#         else:
#             dest_path = f"test_parameters/{os.path.basename(test_param_dir)}"
#             cp_test_parameters_str = f"kubectl cp {test_param_dir} {namespace}/{pod}:{base_dir}/test_parameters/"

#         _logger.info(cp_test_parameters_str)
#         subprocess.run(
#             [cp_test_parameters_str],
#             shell=True,
#             check=False,
#         )

#         test_exists_path_str = (
#             f"kubectl exec {pod} -n {namespace} -- test -e {dest_path}"
#         )
#         _logger.info(
#             f"Checking for path {dest_path} in {namespace}/{pod}:{base_dir}/ ..."
#         )
#         _logger.info(test_exists_path_str)
#         try:
#             subprocess.run(
#                 [test_exists_path_str],
#                 shell=True,
#                 check=True,
#                 text=True,
#             )
#         except subprocess.CalledProcessError as e:
#             _logger.error(
#                 f"Checking for path {namespace}/{pod}:{base_dir}/{dest_path} failed."
#             )
#             raise e

#     _logger.info(
#         f"Done copying the test parameters to pod: {pod}, dir: {base_dir}"
#     )


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


# # check that the MCS pods are running
# @given("that the CBF is in a nominal state")
# def that_the_cbf_is_in_a_nominal_state(namespace, talon_list, hw_config_file):
#     _logger.info("Executing the CBF is in a nominal state check")
#     mcs_pod_list = os.getenv("MCS_POD_LIST").split(",")

#     for pod in mcs_pod_list:
#         assert (
#             utils.return_pod_status(str(pod), namespace) == "Running"
#         ), f"Error: pod {pod} status not Running"


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
