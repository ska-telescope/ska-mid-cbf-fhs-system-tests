import json
import random
import time
from typing import Any

import numpy as np
import pytest
from assertpy import assert_that
from base_tango_test_class import BaseTangoTestClass
from connection_utils import DeviceKey, EmulatorAPIService, EmulatorIPBlockId, InjectorAPIService
from scan_utils import frequency_band_map
from ska_tango_base.control_model import AdminMode, CommunicationStatus, HealthState, ObsState
from tango import DevState


@pytest.mark.H1
@pytest.mark.nightly
class TestScanSequence(BaseTangoTestClass):

    @pytest.fixture(autouse=True)
    def reset_all_bands(self, initialize_with_indices) -> None:
        for fhs_vcc_idx in self.loaded_idxs:
            self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx].command_read_write("Init")
        yield
        for fhs_vcc_idx in self.loaded_idxs:
            self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx].command_read_write("Init")

    @pytest.fixture()
    def reset_wib_registers(self, initialize_with_indices, inject_url) -> None:
        with open("test_parameters/injection_reset_registers_1.json") as reset_event_json_file:
            reset_event_json = json.loads(reset_event_json_file.read())
        for fhs_vcc_idx in self.loaded_idxs:
            InjectorAPIService.send_events_to_ip_block(inject_url, fhs_vcc_idx, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, reset_event_json)
        yield
        for fhs_vcc_idx in self.loaded_idxs:
            InjectorAPIService.send_events_to_ip_block(inject_url, fhs_vcc_idx, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, reset_event_json)

    def post_initialize(self) -> None:
        for i in self.loaded_idxs:
            self.event_tracer.subscribe_event(self.fqdns[DeviceKey.ETHERNET][i], "obsState")
            self.event_tracer.subscribe_event(self.fqdns[DeviceKey.PACKET_VALIDATION][i], "obsState")
            self.event_tracer.subscribe_event(self.fqdns[DeviceKey.WIDEBAND_INPUT_BUFFER][i], "obsState")
            self.event_tracer.subscribe_event(self.fqdns[DeviceKey.ALL_BANDS][i], "longRunningCommandsInQueue")
            self.event_tracer.subscribe_event(self.fqdns[DeviceKey.ALL_BANDS][i], "longRunningCommandInProgress")

    def reset_emulators_and_assert_successful(self, fhs_vcc_idx: int) -> None:
        emulator_url = self.emulator_urls[fhs_vcc_idx]
        for ip_block in EmulatorIPBlockId:
            EmulatorAPIService.post(emulator_url, ip_block, route="recover")

        _, eth_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "RESET")
        _, pv_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "RESET")
        _, wib_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "RESET")

        assert eth_reset
        assert pv_reset
        assert wib_reset

        self.logger.info(f"Emulators were reset successfully for FHS-VCC {fhs_vcc_idx}.")

    def set_admin_mode_and_assert_change_events_occurred(self, fhs_vcc_idx: int, admin_mode: AdminMode) -> None:
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_proxy.write_attribute("adminMode", admin_mode)
        all_bands_opState = all_bands_proxy.read_attribute("State")

        self.logger.debug(f"allbands OpState after setting to {admin_mode.name}: {all_bands_opState}")

        match admin_mode:
            case AdminMode.ONLINE:
                assert all_bands_opState == DevState.ON

                self.logger.info("Waiting for CommunicationState to be ESTABLISHED.")
                assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                    device_name=all_bands_fqdn,
                    attribute_name="communicationState",
                    attribute_value=CommunicationStatus.ESTABLISHED,
                )
                self.logger.info(f"CommunicationState successfully set to ESTABLISHED for FHS-VCC {fhs_vcc_idx}.")

            case AdminMode.OFFLINE:
                all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

                self.logger.info("Waiting for CommunicationState to be DISABLED.")
                assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                    device_name=all_bands_fqdn,
                    attribute_name="communicationState",
                    attribute_value=CommunicationStatus.DISABLED,
                )
                self.logger.info(f"CommunicationState successfully set to DISABLED for FHS-VCC {fhs_vcc_idx}.")
            case _:
                self.logger.warn("Unsupported AdminMode: {admin_mode.name}")

        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")
        self.logger.debug(f"allbands AdminMode after setting to {admin_mode.name}: {all_bands_adminMode}")

        assert all_bands_adminMode == admin_mode

        self.logger.info(f"AdminMode successfully set to {admin_mode.name} for FHS-VCC {fhs_vcc_idx}.")

    def get_configure_scan_config(self, config_path: str) -> tuple[str, dict]:
        with open(config_path, "r") as configure_scan_file:
            configure_scan_data = configure_scan_file.read()
        assert len(configure_scan_data) > 0
        return configure_scan_data, json.loads(configure_scan_data)

    def run_configure_scan(self, fhs_vcc_idx: int, config_str: str) -> Any:
        configure_scan_result = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx].command_read_write("ConfigureScan", config_str)
        self.logger.debug(f"configure scan result: {configure_scan_result}")

        return configure_scan_result

    def run_configure_scan_and_assert_success(self, fhs_vcc_idx: int, config_path: str) -> Any:
        config_str, config_dict = self.get_configure_scan_config(config_path)

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        vcc_123_proxy = self.proxies[DeviceKey.VCC_123][fhs_vcc_idx]
        wfs_proxy = self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx]
        fss_proxy = self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx]
        packetizer_proxy = self.proxies[DeviceKey.PACKETIZER][fhs_vcc_idx]
        emulator_url = self.emulator_urls[fhs_vcc_idx]

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand = all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset = all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status = json.loads(vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status = json.loads(wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status = json.loads(fss_proxy.command_read_write("GetStatus", False)[1][0])
        packetizer_status = json.loads(packetizer_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState before ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand before ConfigureScan: {all_bands_frequencyBand}")
        self.logger.debug(f"allbands frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset}")
        self.logger.debug(f"vcc status before ConfigureScan: {vcc_123_status}")
        self.logger.debug(f"wfs status before ConfigureScan: {wfs_status}")
        self.logger.debug(f"fss status before ConfigureScan: {fss_status}")
        self.logger.debug(f"packetizer status before ConfigureScan: {packetizer_status}")

        configure_scan_result = self.run_configure_scan(fhs_vcc_idx, config_str)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.CONFIGURING,
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{configure_scan_result[1][0]}",
                '[0, "ConfigureScan completed OK"]',
            ),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.READY,
        )

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand = all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset = all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status = json.loads(vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status = json.loads(wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status = json.loads(fss_proxy.command_read_write("GetStatus", False)[1][0])
        packetizer_status = json.loads(packetizer_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState after ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand after ConfigureScan: {all_bands_frequencyBand}")
        self.logger.debug(f"allbands frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset}")
        self.logger.debug(f"vcc status after ConfigureScan: {vcc_123_status}")
        self.logger.debug(f"wfs status after ConfigureScan: {wfs_status}")
        self.logger.debug(f"fss status after ConfigureScan: {fss_status}")
        self.logger.debug(f"packetizer status after ConfigureScan: {packetizer_status}")

        vcc_123_state, vcc_123_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.VCC_123, "ACTIVE")
        wfs_state, wfs_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_FREQ_SHIFTER, "ACTIVE")
        fss_state, fss_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.FREQ_SLICE_SELECTION, "ACTIVE")

        self.logger.debug(f"vcc state after ConfigureScan: {vcc_123_state}")
        self.logger.debug(f"wfs state after ConfigureScan: {wfs_state}")
        self.logger.debug(f"fss state after ConfigureScan: {fss_state}")

        assert vcc_123_active
        assert wfs_active
        assert fss_active

        expected_frequency_band = frequency_band_map.get(config_dict.get("frequency_band"))
        expected_frequency_band_offset = [
            config_dict.get("frequency_band_offset_stream_1"),
            config_dict.get("frequency_band_offset_stream_2"),
        ]

        assert all_bands_frequencyBand == expected_frequency_band
        assert len(all_bands_frequencyBandOffset) == 2
        assert all_bands_frequencyBandOffset[0] == expected_frequency_band_offset[0]
        assert all_bands_frequencyBandOffset[1] == expected_frequency_band_offset[1]

        expected_gains = np.reshape(config_dict.get("vcc_gain"), (-1, 2)).transpose().flatten()
        expected_shift_frequency = expected_frequency_band_offset[0]
        expected_band_select = expected_frequency_band + 1

        vcc_123_gains = vcc_123_status.get("gains")
        assert all(expected_gains[i] == pytest.approx(vcc_123_gains[i].get("gain")) for i in range(len(expected_gains)))
        assert wfs_status.get("shift_frequency") == expected_shift_frequency
        assert fss_status.get("band_select") == expected_band_select

        expected_packetizer_vid = config_dict.get("fs_lanes")[0].get("vlan_id")
        assert packetizer_status.get("vid_register") == expected_packetizer_vid

        self.logger.info(f"ConfigureScan completed successfully for FHS-VCC {fhs_vcc_idx}.")

    def run_configure_scan_and_assert_failure(self, fhs_vcc_idx: int, config_path: str, expected_code: int = 5, expected_error_msg: str | None = None) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        vcc_123_proxy = self.proxies[DeviceKey.VCC_123][fhs_vcc_idx]
        wfs_proxy = self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx]
        fss_proxy = self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx]
        packetizer_proxy = self.proxies[DeviceKey.PACKETIZER][fhs_vcc_idx]
        emulator_url = self.emulator_urls[fhs_vcc_idx]

        config_str, _ = self.get_configure_scan_config(config_path)

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand_before = all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset_before = all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status_before = json.loads(vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status_before = json.loads(wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status_before = json.loads(fss_proxy.command_read_write("GetStatus", False)[1][0])
        packetizer_status_before = json.loads(packetizer_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState before ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand before ConfigureScan: {all_bands_frequencyBand_before}")
        self.logger.debug(f"allbands frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset_before}")
        self.logger.debug(f"vcc status before ConfigureScan: {vcc_123_status_before}")
        self.logger.debug(f"wfs status before ConfigureScan: {wfs_status_before}")
        self.logger.debug(f"fss status before ConfigureScan: {fss_status_before}")
        self.logger.debug(f"packetizer status before ConfigureScan: {packetizer_status_before}")

        configure_scan_result = self.run_configure_scan(fhs_vcc_idx, config_str)

        if expected_error_msg is not None:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=all_bands_fqdn,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{configure_scan_result[1][0]}",
                    f'[{expected_code}, "{expected_error_msg}"]',
                ),
            )

        else:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=all_bands_fqdn,
                attribute_name="longRunningCommandResult",
                custom_matcher=lambda event: event.attribute_value[1].strip("[]").split(",")[0].strip() == f"{expected_code}",
            )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand_after = all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset_after = all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status_after = json.loads(vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status_after = json.loads(wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status_after = json.loads(fss_proxy.command_read_write("GetStatus", False)[1][0])
        packetizer_status_after = json.loads(packetizer_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState after ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand after ConfigureScan: {all_bands_frequencyBand_after}")
        self.logger.debug(f"allbands frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset_after}")
        self.logger.debug(f"vcc status after ConfigureScan: {vcc_123_status_after}")
        self.logger.debug(f"wfs status after ConfigureScan: {wfs_status_after}")
        self.logger.debug(f"fss status after ConfigureScan: {fss_status_after}")
        self.logger.debug(f"packetizer status after ConfigureScan: {packetizer_status_after}")

        vcc_123_state, vcc_123_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.VCC_123, "ACTIVE")
        wfs_state, wfs_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_FREQ_SHIFTER, "ACTIVE")
        fss_state, fss_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.FREQ_SLICE_SELECTION, "ACTIVE")

        self.logger.debug(f"vcc state after ConfigureScan: {vcc_123_state}")
        self.logger.debug(f"wfs state after ConfigureScan: {wfs_state}")
        self.logger.debug(f"fss state after ConfigureScan: {fss_state}")

        assert vcc_123_active
        assert wfs_active
        assert fss_active

        assert all_bands_frequencyBand_after == all_bands_frequencyBand_before
        assert len(all_bands_frequencyBandOffset_after) == 2
        assert all_bands_frequencyBandOffset_after[0] == all_bands_frequencyBandOffset_before[0]
        assert all_bands_frequencyBandOffset_after[1] == all_bands_frequencyBandOffset_before[1]

        vcc_123_gains_before = vcc_123_status_before.get("gains")
        vcc_123_gains_after = vcc_123_status_after.get("gains")
        assert all(vcc_123_gains_before[i].get("gain") == pytest.approx(vcc_123_gains_after[i].get("gain")) for i in range(len(vcc_123_gains_before)))
        assert wfs_status_after.get("shift_frequency") == wfs_status_before.get("shift_frequency")
        assert fss_status_after.get("band_select") == fss_status_before.get("band_select")

        assert packetizer_status_after.get("vid_register") == packetizer_status_before.get("vid_register")

        self.logger.info(f"ConfigureScan failed as expected for FHS-VCC {fhs_vcc_idx}.")

    def run_scan_and_assert_success(self, fhs_vcc_idx: int) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        eth_proxy = self.proxies[DeviceKey.ETHERNET][fhs_vcc_idx]
        pv_proxy = self.proxies[DeviceKey.PACKET_VALIDATION][fhs_vcc_idx]
        wib_proxy = self.proxies[DeviceKey.WIDEBAND_INPUT_BUFFER][fhs_vcc_idx]
        emulator_url = self.emulator_urls[fhs_vcc_idx]

        eth_obsState = eth_proxy.read_attribute("obsState")
        pv_obsState = pv_proxy.read_attribute("obsState")
        wib_obsState = wib_proxy.read_attribute("obsState")

        self.logger.debug(f"Ethernet obsState before Scan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState before Scan: {pv_obsState}")
        self.logger.debug(f"WIB obsState before Scan: {wib_obsState}")

        eth_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "state")
        pv_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "state")
        wib_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "state")

        self.logger.debug(f"eth state before Scan: {eth_state}")
        self.logger.debug(f"pv state before Scan: {pv_state}")
        self.logger.debug(f"wib state before Scan: {wib_state}")

        scan_result = all_bands_proxy.command_read_write("Scan", 0)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx],
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{scan_result[1][0]}",
                '[0, "Scan completed OK"]',
            ),
        )

        for device_key in [DeviceKey.ALL_BANDS, DeviceKey.ETHERNET, DeviceKey.PACKET_VALIDATION, DeviceKey.WIDEBAND_INPUT_BUFFER]:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.fqdns[device_key][fhs_vcc_idx],
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
            )

        all_bands_opState = all_bands_proxy.read_attribute("State")
        assert all_bands_opState == DevState.ON

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        eth_obsState = eth_proxy.read_attribute("obsState")
        pv_obsState = pv_proxy.read_attribute("obsState")
        wib_obsState = wib_proxy.read_attribute("obsState")

        self.logger.debug(f"allbands obsState after Scan: {all_bands_obsState}")
        self.logger.debug(f"Ethernet obsState after Scan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState after Scan: {pv_obsState}")
        self.logger.debug(f"WIB obsState after Scan: {wib_obsState}")

        eth_state, eth_link = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "LINK")
        pv_state, pv_enabled = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "ENABLED")
        wib_state, wib_enabled = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "ENABLED")

        self.logger.debug(f"eth state after Scan: {eth_state}")
        self.logger.debug(f"pv state after Scan: {pv_state}")
        self.logger.debug(f"wib state after Scan: {wib_state}")

        assert eth_link
        assert pv_enabled
        assert wib_enabled

        self.logger.info(f"Scan completed successfully for FHS-VCC {fhs_vcc_idx}.")

    def run_end_scan_and_assert_success(self, fhs_vcc_idx: int) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        emulator_url = self.emulator_urls[fhs_vcc_idx]

        end_scan_result = all_bands_proxy.command_read_write("EndScan")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx],
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{end_scan_result[1][0]}",
                '[0, "EndScan completed OK"]',
            ),
        )

        for device_key in [DeviceKey.ALL_BANDS, DeviceKey.ETHERNET, DeviceKey.PACKET_VALIDATION, DeviceKey.WIDEBAND_INPUT_BUFFER]:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.fqdns[device_key][fhs_vcc_idx],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
            )

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        self.logger.debug(f"allbands obsState after EndScan: {all_bands_obsState}")

        eth_obsState = self.proxies[DeviceKey.ETHERNET][fhs_vcc_idx].read_attribute("obsState")
        pv_obsState = self.proxies[DeviceKey.PACKET_VALIDATION][fhs_vcc_idx].read_attribute("obsState")
        wib_obsState = self.proxies[DeviceKey.WIDEBAND_INPUT_BUFFER][fhs_vcc_idx].read_attribute("obsState")

        self.logger.debug(f"Ethernet obsState after EndScan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState after EndScan: {pv_obsState}")
        self.logger.debug(f"WIB obsState after EndScan: {wib_obsState}")

        eth_state, eth_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "RESET")
        pv_state, pv_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "RESET")
        wib_state, wib_ready = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "READY")

        self.logger.debug(f"eth state after EndScan: {eth_state}")
        self.logger.debug(f"pv state after EndScan: {pv_state}")
        self.logger.debug(f"wib state after EndScan: {wib_state}")

        assert eth_reset
        assert pv_reset
        assert wib_ready

        self.logger.info(f"EndScan completed successfully for FHS-VCC {fhs_vcc_idx}.")

    def run_abort_and_assert_success(self, fhs_vcc_idx: int) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        all_bands_opState = all_bands_proxy.read_attribute("State")
        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_lrcQ = all_bands_proxy.read_attribute("longRunningCommandsInQueue")
        all_bands_lrcP = all_bands_proxy.read_attribute("longRunningCommandInProgress")

        self.logger.debug(f"allbands opState before AbortCommands: {all_bands_opState}")
        self.logger.debug(f"allbands obsState before AbortCommands: {all_bands_obsState}")
        self.logger.debug(f"allbands LRC in Q before AbortCommands: {all_bands_lrcQ}")
        self.logger.debug(f"allbands LRC in Prog before AbortCommands: {all_bands_lrcP}")

        all_bands_proxy.command_read_write("AbortCommands")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.ABORTED,
        )

        for device_key in [DeviceKey.ALL_BANDS, DeviceKey.ETHERNET, DeviceKey.PACKET_VALIDATION, DeviceKey.WIDEBAND_INPUT_BUFFER]:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.fqdns[device_key][fhs_vcc_idx],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
            )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandsInQueue",
            attribute_value=(),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandInProgress",
            attribute_value=(),
        )

        all_bands_opState = all_bands_proxy.read_attribute("State")
        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_lrcQ = all_bands_proxy.read_attribute("longRunningCommandsInQueue")
        all_bands_lrcP = all_bands_proxy.read_attribute("longRunningCommandInProgress")

        self.logger.debug(f"allbands opState after AbortCommands: {all_bands_opState}")
        self.logger.debug(f"allbands obsState after AbortCommands: {all_bands_obsState}")
        self.logger.debug(f"allbands LRC in Q after AbortCommands: {all_bands_lrcQ}")
        self.logger.debug(f"allbands LRC in Prog after AbortCommands: {all_bands_lrcP}")

        self.logger.info(f"AbortCommands completed successfully for FHS-VCC {fhs_vcc_idx}.")

    def run_go_to_idle_and_assert_success(self, fhs_vcc_idx: int) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        go_to_idle_result = all_bands_proxy.command_read_write("GoToIdle")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{go_to_idle_result[1][0]}",
                '[0, "GoToIdle completed OK"]',
            ),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        all_bands_opState = all_bands_proxy.read_attribute("State")
        all_bands_obsState = all_bands_proxy.read_attribute("obsState")

        self.logger.debug(f"allbands opState after GoToIdle: {all_bands_opState}")
        self.logger.debug(f"allbands obsState after GoToIdle: {all_bands_obsState}")

        self.logger.info(f"GoToIdle completed successfully for FHS-VCC {fhs_vcc_idx}.")

    def run_obsreset_and_assert_success(self, fhs_vcc_idx: int) -> Any:

        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        emulator_url = self.emulator_urls[fhs_vcc_idx]

        obsreset_result = all_bands_proxy.command_read_write("ObsReset")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{obsreset_result[1][0]}",
                '[0, "ObsReset completed OK"]',
            ),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        eth_state, eth_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "RESET")
        pv_state, pv_reset = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "RESET")
        wib_state, wib_ready = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "READY")

        self.logger.debug(f"eth state after ObsReset: {eth_state}")
        self.logger.debug(f"pv state after ObsReset: {pv_state}")
        self.logger.debug(f"wib state after ObsReset: {wib_state}")

        assert eth_reset
        assert pv_reset
        assert wib_ready

        all_bands_opState = all_bands_proxy.read_attribute("State")
        all_bands_obsState = all_bands_proxy.read_attribute("obsState")

        self.logger.debug(f"allbands opState after GoToIdle: {all_bands_opState}")
        self.logger.debug(f"allbands obsState after GoToIdle: {all_bands_obsState}")

        self.logger.info(f"ObsReset completed successfully for FHS-VCC {fhs_vcc_idx}.")

    @pytest.mark.dev
    @pytest.mark.parametrize("initialize_with_indices", [1, 3, 5], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_valid_config_single_scan_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        self.logger.info(f'SEQUENTIAL TEST [IDX={fhs_vcc_idx}] STARTED AT: {time.ctime()}')

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Run EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 5. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 6. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [3, 6, 1], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_abort_mid_scan_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Run AbortCommands()

        self.run_abort_and_assert_success(fhs_vcc_idx)

        # 5. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [5, 2, 4], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_obsreset_from_aborted_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Run AbortCommands()

        self.run_abort_and_assert_success(fhs_vcc_idx)

        # 5. Run ObsReset()

        self.run_obsreset_and_assert_success(fhs_vcc_idx)

        # 6. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [2, 4, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_valid_config_two_scans_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run first ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run first Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Run first EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 5. Run second ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_2.json")

        # 6. Run second Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 7. Run second EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 8. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 9. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.dev
    @pytest.mark.parametrize("initialize_with_indices", [[2, 4, 6]], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_parallel_random_order_single_scan_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        self.logger.info(f'PARALLEL TEST STARTED AT: {time.ctime()}')

        all_bands_proxies = self.proxies[DeviceKey.ALL_BANDS]
        configure_scan_results = {}
        config_dicts = {}
        scan_results = {}

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):
            all_bands_proxy = all_bands_proxies[fhs_vcc_idx]

            # Ensure emulators are reset before starting
            self.reset_emulators_and_assert_successful(fhs_vcc_idx)

            all_bands_state = all_bands_proxy.read_attribute("State")
            all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

            self.logger.debug(f"allbands {fhs_vcc_idx} initial OpState: {all_bands_state}")
            self.logger.debug(f"allbands {fhs_vcc_idx} initial AdminMode: {all_bands_adminMode}")

            # 1. Set AdminMode.ONLINE

            self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

            # 2. Run ConfigureScan()'s in parallel with unique configurations

            all_bands_obsState = all_bands_proxy.read_attribute("obsState")
            all_bands_frequencyBand = all_bands_proxy.read_attribute("frequencyBand")
            all_bands_frequencyBandOffset = all_bands_proxy.read_attribute("frequencyBandOffset")
            vcc_123_status = json.loads(self.proxies[DeviceKey.VCC_123][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])
            wfs_status = json.loads(self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])
            fss_status = json.loads(self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])

            self.logger.debug(f"allbands {fhs_vcc_idx} ObsState before ConfigureScan: {all_bands_obsState}")
            self.logger.debug(f"allbands {fhs_vcc_idx} frequencyBand before ConfigureScan: {all_bands_frequencyBand}")
            self.logger.debug(f"allbands {fhs_vcc_idx} frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset}")
            self.logger.debug(f"vcc {fhs_vcc_idx} status before ConfigureScan: {vcc_123_status}")
            self.logger.debug(f"wfs {fhs_vcc_idx} status before ConfigureScan: {wfs_status}")
            self.logger.debug(f"fss {fhs_vcc_idx} status before ConfigureScan: {fss_status}")

            config_str, config_dicts[fhs_vcc_idx] = self.get_configure_scan_config(f"test_parameters/configure_scan_valid_1.json")
            configure_scan_results[fhs_vcc_idx] = self.run_configure_scan(fhs_vcc_idx, config_str)

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):
            all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
            emulator_url = self.emulator_urls[fhs_vcc_idx]

            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=all_bands_fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.CONFIGURING,
            )

            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=all_bands_fqdn,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{configure_scan_results[fhs_vcc_idx][1][0]}",
                    '[0, "ConfigureScan completed OK"]',
                ),
            )

            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=all_bands_fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.READY,
            )

            vcc_123_state, vcc_123_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.VCC_123, "ACTIVE")
            wfs_state, wfs_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_FREQ_SHIFTER, "ACTIVE")
            fss_state, fss_active = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.FREQ_SLICE_SELECTION, "ACTIVE")

            self.logger.debug(f"vcc {fhs_vcc_idx} state after ConfigureScan: {vcc_123_state}")
            self.logger.debug(f"wfs {fhs_vcc_idx} state after ConfigureScan: {wfs_state}")
            self.logger.debug(f"fss {fhs_vcc_idx} state after ConfigureScan: {fss_state}")

            assert vcc_123_active
            assert wfs_active
            assert fss_active

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):
            config_dict = config_dicts[fhs_vcc_idx]
            all_bands_proxy = all_bands_proxies[fhs_vcc_idx]

            all_bands_obsState = all_bands_proxy.read_attribute("obsState")
            all_bands_frequencyBand = all_bands_proxy.read_attribute("frequencyBand")
            all_bands_frequencyBandOffset = all_bands_proxy.read_attribute("frequencyBandOffset")
            vcc_123_status = json.loads(self.proxies[DeviceKey.VCC_123][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])
            wfs_status = json.loads(self.proxies[DeviceKey.WIDEBAND_FREQ_SHIFTER][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])
            fss_status = json.loads(self.proxies[DeviceKey.FREQ_SLICE_SELECTION][fhs_vcc_idx].command_read_write("GetStatus", False)[1][0])

            self.logger.debug(f"allbands {fhs_vcc_idx} ObsState after ConfigureScan: {all_bands_obsState}")
            self.logger.debug(f"allbands {fhs_vcc_idx} frequencyBand after ConfigureScan: {all_bands_frequencyBand}")
            self.logger.debug(f"allbands {fhs_vcc_idx} frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset}")
            self.logger.debug(f"vcc {fhs_vcc_idx} status after ConfigureScan: {vcc_123_status}")
            self.logger.debug(f"wfs {fhs_vcc_idx} status after ConfigureScan: {wfs_status}")
            self.logger.debug(f"fss {fhs_vcc_idx} status after ConfigureScan: {fss_status}")

            expected_frequency_band = frequency_band_map.get(config_dict.get("frequency_band"))
            expected_frequency_band_offset = [
                config_dict.get("frequency_band_offset_stream_1"),
                config_dict.get("frequency_band_offset_stream_2"),
            ]

            assert all_bands_frequencyBand == expected_frequency_band
            assert len(all_bands_frequencyBandOffset) == 2
            assert all_bands_frequencyBandOffset[0] == expected_frequency_band_offset[0]
            assert all_bands_frequencyBandOffset[1] == expected_frequency_band_offset[1]

            expected_gains = np.reshape(config_dict.get("vcc_gain"), (-1, 2)).transpose().flatten()
            expected_shift_frequency = expected_frequency_band_offset[0]
            expected_band_select = expected_frequency_band + 1

            vcc_123_gains = vcc_123_status.get("gains")
            assert all(expected_gains[i] == pytest.approx(vcc_123_gains[i].get("gain")) for i in range(len(expected_gains)))
            assert wfs_status.get("shift_frequency") == expected_shift_frequency
            assert fss_status.get("band_select") == expected_band_select

            self.logger.info(f"ConfigureScan completed successfully for FHS-VCC {fhs_vcc_idx}.")

            # 3. Run Scan()'s in parallel

            all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
            eth_proxy = self.proxies[DeviceKey.ETHERNET][fhs_vcc_idx]
            pv_proxy = self.proxies[DeviceKey.PACKET_VALIDATION][fhs_vcc_idx]
            wib_proxy = self.proxies[DeviceKey.WIDEBAND_INPUT_BUFFER][fhs_vcc_idx]
            emulator_url = self.emulator_urls[fhs_vcc_idx]

            eth_obsState = eth_proxy.read_attribute("obsState")
            pv_obsState = pv_proxy.read_attribute("obsState")
            wib_obsState = wib_proxy.read_attribute("obsState")

            self.logger.debug(f"Ethernet {fhs_vcc_idx} obsState before Scan: {eth_obsState}")
            self.logger.debug(f"Packet Validation {fhs_vcc_idx} obsState before Scan: {pv_obsState}")
            self.logger.debug(f"WIB {fhs_vcc_idx} obsState before Scan: {wib_obsState}")

            eth_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "state")
            pv_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "state")
            wib_state = EmulatorAPIService.get(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "state")

            self.logger.debug(f"eth {fhs_vcc_idx} state before Scan: {eth_state}")
            self.logger.debug(f"pv {fhs_vcc_idx} state before Scan: {pv_state}")
            self.logger.debug(f"wib {fhs_vcc_idx} state before Scan: {wib_state}")

            scan_results[fhs_vcc_idx] = all_bands_proxy.command_read_write("Scan", 0)

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):
            all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]
            emulator_url = self.emulator_urls[fhs_vcc_idx]

            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx],
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{scan_results[fhs_vcc_idx][1][0]}",
                    '[0, "Scan completed OK"]',
                ),
            )

            for device_key in [DeviceKey.ALL_BANDS, DeviceKey.ETHERNET, DeviceKey.PACKET_VALIDATION, DeviceKey.WIDEBAND_INPUT_BUFFER]:
                assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                    device_name=self.fqdns[device_key][fhs_vcc_idx],
                    attribute_name="obsState",
                    attribute_value=ObsState.SCANNING,
                )

            eth_state, eth_link = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.ETHERNET_200G, "LINK")
            pv_state, pv_enabled = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "ENABLED")
            wib_state, wib_enabled = EmulatorAPIService.wait_for_state(emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "ENABLED")

            self.logger.debug(f"eth {fhs_vcc_idx} state after Scan: {eth_state}")
            self.logger.debug(f"pv {fhs_vcc_idx} state after Scan: {pv_state}")
            self.logger.debug(f"wib {fhs_vcc_idx} state after Scan: {wib_state}")

            assert eth_link
            assert pv_enabled
            assert wib_enabled

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):
            all_bands_opState = all_bands_proxy.read_attribute("State")
            assert all_bands_opState == DevState.ON

            all_bands_obsState = all_bands_proxy.read_attribute("obsState")
            eth_obsState = eth_proxy.read_attribute("obsState")
            pv_obsState = pv_proxy.read_attribute("obsState")
            wib_obsState = wib_proxy.read_attribute("obsState")

            self.logger.debug(f"allbands {fhs_vcc_idx} obsState after Scan: {all_bands_obsState}")
            self.logger.debug(f"Ethernet {fhs_vcc_idx} obsState after Scan: {eth_obsState}")
            self.logger.debug(f"Packet Validation {fhs_vcc_idx} obsState after Scan: {pv_obsState}")
            self.logger.debug(f"WIB {fhs_vcc_idx} obsState after Scan: {wib_obsState}")

            self.logger.info(f"Scan completed successfully for FHS-VCC {fhs_vcc_idx}.")

        # 4. Teardown (sequential)

        for fhs_vcc_idx in random.sample(self.loaded_idxs, k=len(self.loaded_idxs)):

            # 5. Run EndScan()

            self.run_end_scan_and_assert_success(fhs_vcc_idx)

            # 6. Run GoToIdle()

            self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

            # 7. Set AdminMode.OFFLINE

            self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

            self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [1, 4, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_invalid_config_schema_mismatch_single_scan_error(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_failure(
            fhs_vcc_idx, "test_parameters/configure_scan_invalid_schema_mismatch.json", 5, "Arg provided does not match schema for ConfigureScan"
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx],
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        # 3. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [2, 4, 5], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_invalid_config_bad_gains_single_scan_error(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_failure(fhs_vcc_idx, "test_parameters/configure_scan_invalid_wrong_num_gains.json", 3)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx],
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        # 3. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [2, 5, 1], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_invalid_config_then_reconfigure_with_valid_config_single_scan_success(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run first ConfigureScan()

        self.run_configure_scan_and_assert_failure(fhs_vcc_idx, "test_parameters/configure_scan_invalid_schema_mismatch.json")
        time.sleep(10)
        # 3. Run second ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 4. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 5. Run EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 6. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 7. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [1, 3, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_commands_out_of_order_error(self, initialize_with_indices) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Run ConfigureScan() again (incorrect)

        self.run_configure_scan_and_assert_failure(fhs_vcc_idx, "test_parameters/configure_scan_valid_2.json", 5)

        # 5. Run EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 6. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 7. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [5, 1, 4], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_inject_bad_dish_id_sets_health_state_failed(self, initialize_with_indices, inject_url, reset_wib_registers) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Inject new dish ID to the WIB to cause FAILED health state

        with open("test_parameters/injection_change_dish_id_1.json") as event_json_file:
            event_json = json.loads(event_json_file.read())

        InjectorAPIService.send_events_to_ip_block(inject_url, fhs_vcc_idx, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, event_json)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="healthState",
            attribute_value=HealthState.FAILED,
        )

        # 5. Run EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 6. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 7. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [2, 3, 6], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_inject_fault_then_reconfigure_success(self, initialize_with_indices, inject_url, reset_wib_registers) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run first ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run first Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Inject new dish ID to the WIB to cause FAILED health state

        with open("test_parameters/injection_change_dish_id_1.json") as event_json_file:
            event_json = json.loads(event_json_file.read())

        InjectorAPIService.send_events_to_ip_block(inject_url, fhs_vcc_idx, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, event_json)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="healthState",
            attribute_value=HealthState.FAILED,
        )

        # 5. Run first EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 6. Run second ConfigureScan() to match injected dish ID

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1_changed_dish_id.json")

        # 7. Run second Scan(), should now be in health state OK

        self.run_scan_and_assert_success(fhs_vcc_idx)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="healthState",
            attribute_value=HealthState.OK,
        )

        # 8. Run second EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 9. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 10. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

    @pytest.mark.parametrize("initialize_with_indices", [5, 1, 4], ids=lambda i: f"fhs_vcc_idx={i}", indirect=["initialize_with_indices"])
    def test_scan_sequence_inject_bad_sample_rate_sets_health_state_failed(self, initialize_with_indices, inject_url, reset_wib_registers) -> None:
        # 0. Initial setup

        fhs_vcc_idx = self.loaded_idxs[0]
        all_bands_proxy = self.proxies[DeviceKey.ALL_BANDS][fhs_vcc_idx]
        all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][fhs_vcc_idx]

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful(fhs_vcc_idx)

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success(fhs_vcc_idx, "test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success(fhs_vcc_idx)

        # 4. Inject new dish ID to the WIB to cause FAILED health state

        with open("test_parameters/injection_change_sample_rate_1.json") as event_json_file:
            event_json = json.loads(event_json_file.read())

        InjectorAPIService.send_events_to_ip_block(inject_url, fhs_vcc_idx, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, event_json)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="healthState",
            attribute_value=HealthState.FAILED,
        )

        # 5. Run EndScan()

        self.run_end_scan_and_assert_success(fhs_vcc_idx)

        # 6. Run GoToIdle()

        self.run_go_to_idle_and_assert_success(fhs_vcc_idx)

        # 7. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(fhs_vcc_idx, AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful(fhs_vcc_idx)
