from __future__ import annotations

from logging import Logger

import pytest
from connection_utils import EmulatorAPIService
from pytango_client_wrapper import PyTangoClientWrapper
from tango import DevState


@pytest.mark.nightly
class TestInitDeployment:

    @pytest.fixture(scope="class")
    def device_idx(self) -> int:
        return 1

    def test_device_server_deployment(
        self: TestInitDeployment,
        logger: Logger,
        eth_proxy: PyTangoClientWrapper,
        pv_proxy: PyTangoClientWrapper,
        wfs_proxy: PyTangoClientWrapper,
        wib_proxy: PyTangoClientWrapper,
        vcc_123_proxy: PyTangoClientWrapper,
        fss_proxy: PyTangoClientWrapper,
        device_idx: int,
    ):
        mac200_000_state = eth_proxy.read_attribute("State")
        vcc_000_state = vcc_123_proxy.read_attribute("State")
        fss_000_state = fss_proxy.read_attribute("State")
        wfs_000_state = wfs_proxy.read_attribute("State")
        wib_000_state = wib_proxy.read_attribute("State")
        pv_000_state = pv_proxy.read_attribute("State")

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

    def test_init_emulators(
        self: TestInitDeployment,
        emulator_url: str,
        device_idx: int,
    ):
        emulator1_json = EmulatorAPIService.get(emulator_url, route="state")
        assert emulator1_json.get("current_state") == "RUNNING"

    def test_device_servers_to_emulator_connection(
        self: TestInitDeployment,
        logger: Logger,
        eth_proxy: PyTangoClientWrapper,
        pv_proxy: PyTangoClientWrapper,
        wfs_proxy: PyTangoClientWrapper,
        wib_proxy: PyTangoClientWrapper,
        vcc_123_proxy: PyTangoClientWrapper,
        fss_proxy: PyTangoClientWrapper,
        device_idx: int,
    ):
        mac200_status = eth_proxy.command_read_write("getstatus", False)
        vcc_status = vcc_123_proxy.command_read_write("getstatus", False)
        fss_status = fss_proxy.command_read_write("getstatus", False)
        wfs_status = wfs_proxy.command_read_write("getstatus", False)
        wib_status = wib_proxy.command_read_write("getstatus", False)
        pv_status = pv_proxy.command_read_write("getstatus", False)

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
