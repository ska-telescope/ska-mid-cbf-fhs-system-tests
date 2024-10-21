from __future__ import annotations

import pytest
import requests
from pytango_client_wrapper import PyTangoClientWrapper
from tango import DevState


@pytest.mark.nightly
class TestInitDeployment:

    def test_device_server_deployment(self: TestInitDeployment, logger):
        mac200_000_proxy = PyTangoClientWrapper()
        vcc_000_proxy = PyTangoClientWrapper()
        fss_000_proxy = PyTangoClientWrapper()
        wfs_000_proxy = PyTangoClientWrapper()
        wib_000_proxy = PyTangoClientWrapper()
        pv_000_proxy = PyTangoClientWrapper()

        mac200_000_proxy.create_tango_client("fhs/mac200/000")
        vcc_000_proxy.create_tango_client("fhs/vcc/000")
        fss_000_proxy.create_tango_client("fhs/frequency-slice-selection/000")
        wfs_000_proxy.create_tango_client("fhs/wfs/000")
        wib_000_proxy.create_tango_client("fhs/wib/000")
        pv_000_proxy.create_tango_client("fhs/packetvalidation/000")

        mac200_000_state = mac200_000_proxy.read_attribute("State")
        vcc_000_state = vcc_000_proxy.read_attribute("State")
        fss_000_state = fss_000_proxy.read_attribute("State")
        wfs_000_state = wfs_000_proxy.read_attribute("State")
        wib_000_state = wib_000_proxy.read_attribute("State")
        pv_000_state = pv_000_proxy.read_attribute("State")

        logger.debug(f"mac200 state {mac200_000_state}")
        logger.debug(f"vcc state {vcc_000_state}")
        logger.debug(f"fss state {fss_000_state}")
        logger.debug(f"wfs state {wfs_000_state}")
        logger.debug(f"wib state {wib_000_state}")
        logger.debug(f"pv state {pv_000_state}")

        assert mac200_000_state == DevState.ON
        assert vcc_000_state == DevState.ON
        assert fss_000_state == DevState.ON
        assert wfs_000_state == DevState.ON
        assert wib_000_state == DevState.ON
        assert pv_000_state == DevState.ON

    def test_init_emulators(self: TestInitDeployment, namespace, cluster_domain):
        response: requests.Response = requests.get(f"http://fhs-vcc-emulator-1.{namespace}.svc.{cluster_domain}:5001/state", timeout=60)
        emulator1_json = response.json()

        assert emulator1_json["current_state"] == "RUNNING"

    def test_device_servers_to_emulator_connection(self: TestInitDeployment, logger):

        mac200_000_proxy = PyTangoClientWrapper()
        vcc_000_proxy = PyTangoClientWrapper()
        fss_000_proxy = PyTangoClientWrapper()
        wfs_000_proxy = PyTangoClientWrapper()
        wib_000_proxy = PyTangoClientWrapper()
        pv_000_proxy = PyTangoClientWrapper()

        mac200_000_proxy.create_tango_client("fhs/mac200/000")
        vcc_000_proxy.create_tango_client("fhs/vcc/000")
        fss_000_proxy.create_tango_client("fhs/frequency-slice-selection/000")
        wfs_000_proxy.create_tango_client("fhs/wfs/000")
        wib_000_proxy.create_tango_client("fhs/wib/000")
        pv_000_proxy.create_tango_client("fhs/packetvalidation/000")

        mac200_status = mac200_000_proxy.command_read_write("getstatus", False)
        vcc_status = vcc_000_proxy.command_read_write("getstatus", False)
        fss_status = fss_000_proxy.command_read_write("getstatus", False)
        wfs_status = wfs_000_proxy.command_read_write("getstatus", False)
        wib_status = wib_000_proxy.command_read_write("getstatus", False)
        pv_status = pv_000_proxy.command_read_write("getstatus", False)

        logger.debug(f"......Mac200Stats: {mac200_status}......")
        logger.debug(f"......Mac200Stats: {mac200_status[0]}......")
        logger.debug(f"......Mac200Stats: {mac200_status[1]}......")

        assert mac200_status is not None
        assert vcc_status is not None
        assert fss_status is not None
        assert fss_status is not None
        assert wfs_status is not None
        assert wib_status is not None
        assert pv_status is not None
