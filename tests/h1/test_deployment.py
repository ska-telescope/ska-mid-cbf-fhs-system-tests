from __future__ import annotations

import pytest
from base_tango_test_class import BaseTangoTestClass
from connection_utils import DeviceKey, EmulatorAPIService
from tango import DevState


@pytest.mark.H1
@pytest.mark.deployment
@pytest.mark.nightly
class TestDeployment(BaseTangoTestClass):

    @pytest.mark.parametrize("initialize_with_indices", [1, [2, 3]], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_device_servers_are_deployed_and_opstate_is_on(self: TestDeployment, initialize_with_indices):
        fhs_vcc_idx = self.idxs[0]

        mac200_000_state = self.proxies[DeviceKey.ETHERNET][fhs_vcc_idx].read_attribute("State")
        vcc_000_state = self.proxies[DeviceKey.VCC_123][fhs_vcc_idx].read_attribute("State")
        fss_000_state = self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx].read_attribute("State")
        wfs_000_state = self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx].read_attribute("State")
        wib_000_state = self.proxies[DeviceKey.WIDEBAND_INPUT_BUFFER][fhs_vcc_idx].read_attribute("State")
        pv_000_state = self.proxies[DeviceKey.PACKET_VALIDATION][fhs_vcc_idx].read_attribute("State")

        self.logger.info(f"200Gb Ethernet state is: {mac200_000_state}")
        self.logger.info(f"B123-VCC state is: {vcc_000_state}")
        self.logger.info(f"Frequency Slice Selection state is: {fss_000_state}")
        self.logger.info(f"Wideband Frequency Shifter state is: {wfs_000_state}")
        self.logger.info(f"Wideband Input Buffer state is: {wib_000_state}")
        self.logger.info(f"Packet Validation state is: {pv_000_state}")

        assert mac200_000_state == DevState.ON
        assert vcc_000_state == DevState.ON
        assert fss_000_state == DevState.ON
        assert wfs_000_state == DevState.ON
        assert wib_000_state == DevState.ON
        assert pv_000_state == DevState.ON

    @pytest.mark.parametrize("initialize_with_indices", [1, [2, 3]], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_emulator_is_deployed_and_running(self: TestDeployment, initialize_with_indices):
        emulator1_json = EmulatorAPIService.get(self.emulator_urls[self.idxs[0]], route="state")
        self.logger.info(f"Emulator state is: {emulator1_json.get('current_state', 'None')}")
        assert emulator1_json.get("current_state") == "RUNNING"

    @pytest.mark.parametrize("initialize_with_indices", [1, [2, 3]], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_device_servers_can_send_emulator_api_requests_and_get_responses(self: TestDeployment, initialize_with_indices):
        fhs_vcc_idx = self.idxs[0]

        mac200_status = self.proxies[DeviceKey.ETHERNET][fhs_vcc_idx].command_read_write("getstatus", False)
        vcc_status = self.proxies[DeviceKey.VCC_123][fhs_vcc_idx].command_read_write("getstatus", False)
        fss_status = self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx].command_read_write("getstatus", False)
        wfs_status = self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx].command_read_write("getstatus", False)
        wib_status = self.proxies[DeviceKey.WIDEBAND_INPUT_BUFFER][fhs_vcc_idx].command_read_write("getstatus", False)
        pv_status = self.proxies[DeviceKey.PACKET_VALIDATION][fhs_vcc_idx].command_read_write("getstatus", False)

        self.logger.debug(f"......Mac200Stats: {mac200_status}......")
        self.logger.debug(f"......Mac200Stats: {mac200_status[0]}......")
        self.logger.debug(f"......Mac200Stats: {mac200_status[1]}......")

        assert mac200_status is not None
        assert vcc_status is not None
        assert fss_status is not None
        assert fss_status is not None
        assert wfs_status is not None
        assert wib_status is not None
        assert pv_status is not None
