from __future__ import annotations

import pytest
from base_tango_test_class import BaseTangoTestClass
from connection_utils import DeviceKey, EmulatorAPIService
from tango import DevState


@pytest.mark.H1
@pytest.mark.deployment
@pytest.mark.nightly
class TestDeployment(BaseTangoTestClass):

    @pytest.mark.parametrize("initialize_with_indices", [1, 2, 3, 4, 5, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    @pytest.mark.parametrize("device_key", DeviceKey)
    def test_device_servers_are_deployed_and_opstate_is_on(self: TestDeployment, initialize_with_indices, device_key):
        fhs_vcc_idx = self.loaded_idxs[0]
        state = self.proxies[device_key][fhs_vcc_idx].read_attribute("State")
        self.logger.info(f"{device_key} state is: {state}")
        assert state == DevState.ON

    @pytest.mark.parametrize("initialize_with_indices", [1, 2, 3, 4, 5, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_emulator_is_deployed_and_running(self: TestDeployment, initialize_with_indices):
        emulator1_json = EmulatorAPIService.get(self.emulator_urls[self.loaded_idxs[0]], route="state")
        self.logger.info(f"Emulator state is: {emulator1_json.get('current_state', 'None')}")
        assert emulator1_json.get("current_state") == "RUNNING"

    @pytest.mark.parametrize("initialize_with_indices", [1, 2, 3, 4, 5, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    @pytest.mark.parametrize("device_key", DeviceKey)
    def test_device_servers_can_send_emulator_api_requests_and_get_responses(self: TestDeployment, initialize_with_indices, device_key):
        if device_key == DeviceKey.ALL_BANDS:
            # all bands does not expose getstatus
            return
        fhs_vcc_idx = self.loaded_idxs[0]
        status = self.proxies[device_key][fhs_vcc_idx].command_read_write("getstatus", False)
        self.logger.debug(f"......{device_key} Status: {status}......")
        assert status is not None
