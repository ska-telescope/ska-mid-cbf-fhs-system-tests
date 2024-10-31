import json
from logging import Logger
from typing import Any

import numpy as np
import pytest
from assertpy import assert_that
from connection_utils import EmulatorAPIService, EmulatorIPBlockId
from pytango_client_wrapper import PyTangoClientWrapper
from scan_utils import frequency_band_map
from ska_tango_base.control_model import AdminMode, CommunicationStatus, ObsState
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState


@pytest.mark.H1
@pytest.mark.nightly
class TestScanSequence:

    @pytest.fixture(scope="function")
    def event_tracer(
        self,
        all_bands_fqdn: str,
        eth_fqdn: str,
        pv_fqdn: str,
        wib_fqdn: str,
        fhs_vcc_idx: int,
    ) -> TangoEventTracer:
        tracer = TangoEventTracer()

        tracer.subscribe_event(all_bands_fqdn, "longRunningCommandResult")
        tracer.subscribe_event(all_bands_fqdn, "adminMode")
        tracer.subscribe_event(all_bands_fqdn, "state")
        tracer.subscribe_event(all_bands_fqdn, "obsState")
        tracer.subscribe_event(all_bands_fqdn, "communicationState")

        tracer.subscribe_event(eth_fqdn, "obsState")
        tracer.subscribe_event(pv_fqdn, "obsState")
        tracer.subscribe_event(wib_fqdn, "obsState")

        return tracer

    @pytest.fixture(autouse=True)
    def reset_all_bands(self, all_bands_proxy: PyTangoClientWrapper, fhs_vcc_idx: int) -> None:
        all_bands_proxy.command_read_write("Init")
        yield
        all_bands_proxy.command_read_write("Init")

    @pytest.fixture(scope="function", autouse=True)
    def set_fixture_class_vars(
        self,
        logger: Logger,
        all_bands_fqdn: str,
        eth_fqdn: str,
        pv_fqdn: str,
        wib_fqdn: str,
        all_bands_proxy: PyTangoClientWrapper,
        eth_proxy: PyTangoClientWrapper,
        pv_proxy: PyTangoClientWrapper,
        wib_proxy: PyTangoClientWrapper,
        wfs_proxy: PyTangoClientWrapper,
        vcc_123_proxy: PyTangoClientWrapper,
        fss_proxy: PyTangoClientWrapper,
        event_tracer: TangoEventTracer,
        emulator_url: str,
        fhs_vcc_idx: int,
    ) -> None:
        self.logger = logger
        self.all_bands_fqdn = all_bands_fqdn
        self.eth_fqdn = eth_fqdn
        self.pv_fqdn = pv_fqdn
        self.wib_fqdn = wib_fqdn
        self.all_bands_proxy = all_bands_proxy
        self.eth_proxy = eth_proxy
        self.pv_proxy = pv_proxy
        self.wib_proxy = wib_proxy
        self.wfs_proxy = wfs_proxy
        self.vcc_123_proxy = vcc_123_proxy
        self.fss_proxy = fss_proxy
        self.event_tracer = event_tracer
        self.emulator_url = emulator_url

    def reset_emulators_and_assert_successful(self) -> None:
        for ip_block in EmulatorIPBlockId:
            EmulatorAPIService.post(self.emulator_url, ip_block, route="recover")

        _, eth_reset = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.ETHERNET_200G, "RESET")
        _, pv_reset = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "RESET")
        _, wib_reset = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "RESET")

        assert eth_reset
        assert pv_reset
        assert wib_reset

        self.logger.info("Emulators were reset successfully.")

    def set_admin_mode_and_assert_change_events_occurred(self, admin_mode: AdminMode) -> None:
        self.all_bands_proxy.write_attribute("adminMode", admin_mode)
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")
        all_bands_opState = self.all_bands_proxy.read_attribute("State")

        self.logger.debug(f"allbands AdminMode after setting to {admin_mode.name}: {all_bands_adminMode}")
        self.logger.debug(f"allbands OpState after setting to {admin_mode.name}: {all_bands_opState}")

        assert all_bands_adminMode == admin_mode

        self.logger.info(f"AdminMode successfully set to {admin_mode.name}.")

        match admin_mode:
            case AdminMode.ONLINE:
                assert all_bands_opState == DevState.ON

                self.logger.info("Waiting for CommunicationState to be ESTABLISHED.")
                assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                    device_name=self.all_bands_fqdn,
                    attribute_name="communicationState",
                    attribute_value=CommunicationStatus.ESTABLISHED,
                )
                self.logger.info("CommunicationState successfully set to ESTABLISHED.")

            case AdminMode.OFFLINE:
                all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

                self.logger.info("Waiting for CommunicationState to be DISABLED.")
                assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                    device_name=self.all_bands_fqdn,
                    attribute_name="communicationState",
                    attribute_value=CommunicationStatus.DISABLED,
                )
                self.logger.info("CommunicationState successfully set to DISABLED.")
            case _:
                self.logger.warn("Unsupported AdminMode: {admin_mode.name}")

    def get_configure_scan_config(self, config_path: str) -> tuple[str, dict]:
        with open(config_path, "r") as configure_scan_file:
            configure_scan_data = configure_scan_file.read()
        assert len(configure_scan_data) > 0
        return configure_scan_data, json.loads(configure_scan_data)

    def run_configure_scan(self, config_str: str) -> Any:
        configure_scan_result = self.all_bands_proxy.command_read_write("ConfigureScan", config_str)
        self.logger.debug(f"configure scan result: {configure_scan_result[1][0]}")

        return configure_scan_result

    def run_configure_scan_and_assert_success(self, config_path: str) -> Any:
        config_str, config_dict = self.get_configure_scan_config(config_path)

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand = self.all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset = self.all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status = json.loads(self.vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status = json.loads(self.wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status = json.loads(self.fss_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState before ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand before ConfigureScan: {all_bands_frequencyBand}")
        self.logger.debug(f"allbands frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset}")
        self.logger.debug(f"vcc status before ConfigureScan: {vcc_123_status}")
        self.logger.debug(f"wfs status before ConfigureScan: {wfs_status}")
        self.logger.debug(f"fss status before ConfigureScan: {fss_status}")

        configure_scan_result = self.run_configure_scan(config_str)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.CONFIGURING,
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{configure_scan_result[1][0]}",
                '[0, "ConfigureScan completed OK"]',
            ),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.READY,
        )

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand = self.all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset = self.all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status = json.loads(self.vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status = json.loads(self.wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status = json.loads(self.fss_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState after ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand after ConfigureScan: {all_bands_frequencyBand}")
        self.logger.debug(f"allbands frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset}")
        self.logger.debug(f"vcc status after ConfigureScan: {vcc_123_status}")
        self.logger.debug(f"wfs status after ConfigureScan: {wfs_status}")
        self.logger.debug(f"fss status after ConfigureScan: {fss_status}")

        vcc_123_state, vcc_123_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.VCC_123, "ACTIVE")
        wfs_state, wfs_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.WIDEBAND_FREQ_SHIFTER, "ACTIVE")
        fss_state, fss_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.FREQ_SLICE_SELECTION, "ACTIVE")

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

        self.logger.info("ConfigureScan completed successfully.")

    
    def run_configure_scan_and_assert_failure(self, config_path: str, expected_error_msg: str | None = None) -> Any:
        config_str, config_dict = self.get_configure_scan_config(config_path)

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand_before = self.all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset_before = self.all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status_before = json.loads(self.vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status_before = json.loads(self.wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status_before = json.loads(self.fss_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState before ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand before ConfigureScan: {all_bands_frequencyBand_before}")
        self.logger.debug(f"allbands frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset_before}")
        self.logger.debug(f"vcc status before ConfigureScan: {vcc_123_status_before}")
        self.logger.debug(f"wfs status before ConfigureScan: {wfs_status_before}")
        self.logger.debug(f"fss status before ConfigureScan: {fss_status_before}")

        configure_scan_result = self.run_configure_scan(config_str)

        if expected_error_msg is not None: 
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.all_bands_fqdn,
                attribute_name="longRunningCommandResult",
                attribute_value=(
                    f"{configure_scan_result[1][0]}",
                    f'[5, "{expected_error_msg}"]',
                ),
            )

        else:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=self.all_bands_fqdn,
                attribute_name="longRunningCommandResult",
                custom_matcher=lambda event: event.attribute_value[1].strip("[]").split(',')[0].strip() == "5"
            )

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand_after = self.all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset_after = self.all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status_after = json.loads(self.vcc_123_proxy.command_read_write("GetStatus", False)[1][0])
        wfs_status_after = json.loads(self.wfs_proxy.command_read_write("GetStatus", False)[1][0])
        fss_status_after = json.loads(self.fss_proxy.command_read_write("GetStatus", False)[1][0])

        self.logger.debug(f"allbands ObsState after ConfigureScan: {all_bands_obsState}")
        self.logger.debug(f"allbands frequencyBand after ConfigureScan: {all_bands_frequencyBand_after}")
        self.logger.debug(f"allbands frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset_after}")
        self.logger.debug(f"vcc status after ConfigureScan: {vcc_123_status_after}")
        self.logger.debug(f"wfs status after ConfigureScan: {wfs_status_after}")
        self.logger.debug(f"fss status after ConfigureScan: {fss_status_after}")

        vcc_123_state, vcc_123_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.VCC_123, "ACTIVE")
        wfs_state, wfs_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.WIDEBAND_FREQ_SHIFTER, "ACTIVE")
        fss_state, fss_active = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.FREQ_SLICE_SELECTION, "ACTIVE")

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

        self.logger.info("ConfigureScan failed as expected.")
    

    def run_scan_and_assert_success(self) -> Any:
        eth_obsState = self.eth_proxy.read_attribute("obsState")
        pv_obsState = self.pv_proxy.read_attribute("obsState")
        wib_obsState = self.wib_proxy.read_attribute("obsState")

        self.logger.debug(f"Ethernet obsState before Scan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState before Scan: {pv_obsState}")
        self.logger.debug(f"WIB obsState before Scan: {wib_obsState}")

        eth_state = EmulatorAPIService.get(self.emulator_url, EmulatorIPBlockId.ETHERNET_200G, "state")
        pv_state = EmulatorAPIService.get(self.emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "state")
        wib_state = EmulatorAPIService.get(self.emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "state")

        self.logger.debug(f"eth state before Scan: {eth_state}")
        self.logger.debug(f"pv state before Scan: {pv_state}")
        self.logger.debug(f"wib state before Scan: {wib_state}")

        scan_result = self.all_bands_proxy.command_read_write("Scan", 0)

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{scan_result[1][0]}",
                '[0, "Scan completed OK"]',
            ),
        )

        for fqdn in [self.all_bands_fqdn, self.eth_fqdn, self.pv_fqdn, self.wib_fqdn]:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
            )

        all_bands_opState = self.all_bands_proxy.read_attribute("State")
        assert all_bands_opState == DevState.ON

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        eth_obsState = self.eth_proxy.read_attribute("obsState")
        pv_obsState = self.pv_proxy.read_attribute("obsState")
        wib_obsState = self.wib_proxy.read_attribute("obsState")

        self.logger.debug(f"allbands obsState after Scan: {all_bands_obsState}")
        self.logger.debug(f"Ethernet obsState after Scan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState after Scan: {pv_obsState}")
        self.logger.debug(f"WIB obsState after Scan: {wib_obsState}")

        eth_state, eth_link = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.ETHERNET_200G, "LINK")
        pv_state, pv_enabled = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "ENABLED")
        wib_state, wib_enabled = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "ENABLED")

        self.logger.debug(f"eth state after Scan: {eth_state}")
        self.logger.debug(f"pv state after Scan: {pv_state}")
        self.logger.debug(f"wib state after Scan: {wib_state}")

        assert eth_link
        assert pv_enabled
        assert wib_enabled

        self.logger.info("Scan completed successfully.")


    def run_end_scan_and_assert_success(self) -> Any:
        end_scan_result = self.all_bands_proxy.command_read_write("EndScan")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{end_scan_result[1][0]}",
                '[0, "EndScan completed OK"]',
            ),
        )

        for fqdn in [self.all_bands_fqdn, self.eth_fqdn, self.pv_fqdn, self.wib_fqdn]:
            assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.READY,
            )

        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")
        self.logger.debug(f"allbands obsState after EndScan: {all_bands_obsState}")

        eth_obsState = self.eth_proxy.read_attribute("obsState")
        pv_obsState = self.pv_proxy.read_attribute("obsState")
        wib_obsState = self.wib_proxy.read_attribute("obsState")

        self.logger.debug(f"Ethernet obsState after EndScan: {eth_obsState}")
        self.logger.debug(f"Packet Validation obsState after EndScan: {pv_obsState}")
        self.logger.debug(f"WIB obsState after EndScan: {wib_obsState}")

        eth_state, eth_reset = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.ETHERNET_200G, "RESET")
        pv_state, pv_reset = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.PACKET_VALIDATION, "RESET")
        wib_state, wib_ready = EmulatorAPIService.wait_for_state(self.emulator_url, EmulatorIPBlockId.WIDEBAND_INPUT_BUFFER, "READY")

        self.logger.debug(f"eth state after EndScan: {eth_state}")
        self.logger.debug(f"pv state after EndScan: {pv_state}")
        self.logger.debug(f"wib state after EndScan: {wib_state}")

        assert eth_reset
        assert pv_reset
        assert wib_ready

        self.logger.info("EndScan completed successfully.")

    def run_go_to_idle_and_assert_success(self) -> Any:
        go_to_idle_result = self.all_bands_proxy.command_read_write("GoToIdle")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{go_to_idle_result[1][0]}",
                '[0, "GoToIdle completed OK"]',
            ),
        )

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        all_bands_opState = self.all_bands_proxy.read_attribute("State")
        all_bands_obsState = self.all_bands_proxy.read_attribute("obsState")

        self.logger.debug(f"allbands opState after GoToIdle: {all_bands_opState}")
        self.logger.debug(f"allbands obsState after GoToIdle: {all_bands_obsState}")

        self.logger.info("GoToIdle completed successfully.")

    @pytest.mark.dev
    @pytest.mark.parametrize("fhs_vcc_idx", [1, 2], ids=lambda i: f"fhs_vcc_idx={i}")
    def test_scan_sequence_valid_config_single_scan_success(self, fhs_vcc_idx: int) -> None:
        # 0. Initial setup

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful()

        all_bands_state = self.all_bands_proxy.read_attribute("State")
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success("test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success()

        # 4. Run EndScan()

        self.run_end_scan_and_assert_success()

        # 5. Run GoToIdle()

        self.run_go_to_idle_and_assert_success()

        # 6. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful()

    @pytest.mark.parametrize("fhs_vcc_idx", [1, 2, 3, 4, 5, 6], ids=lambda i: f"fhs_vcc_idx={i}")
    def test_scan_sequence_valid_config_two_scans_success(self, fhs_vcc_idx: int) -> None:
        # 0. Initial setup

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful()

        all_bands_state = self.all_bands_proxy.read_attribute("State")
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.ONLINE)

        # 2. Run first ConfigureScan()

        self.run_configure_scan_and_assert_success("test_parameters/configure_scan_valid_1.json")

        # 3. Run first Scan()

        self.run_scan_and_assert_success()

        # 4. Run first EndScan()

        self.run_end_scan_and_assert_success()

        # 5. Run second ConfigureScan()

        self.run_configure_scan_and_assert_success("test_parameters/configure_scan_valid_2.json")

        # 6. Run second Scan()

        self.run_scan_and_assert_success()

        # 7. Run second EndScan()

        self.run_end_scan_and_assert_success()

        # 8. Run GoToIdle()

        self.run_go_to_idle_and_assert_success()

        # 9. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful()
    
    @pytest.mark.parametrize("fhs_vcc_idx", [1, 3], ids=lambda i: f"fhs_vcc_idx={i}")
    def test_scan_sequence_invalid_config_schema_mismatch_single_scan_error(self, fhs_vcc_idx: int) -> None:
        # 0. Initial setup

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful()

        all_bands_state = self.all_bands_proxy.read_attribute("State")
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_failure("test_parameters/configure_scan_invalid_1.json", "Arg provided does not match schema for ConfigureScan")
        
        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        # 3. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful()
    

    @pytest.mark.parametrize("fhs_vcc_idx", [1], ids=lambda i: f"fhs_vcc_idx={i}")
    def test_scan_sequence_invalid_config_bad_gains_single_scan_error(self, fhs_vcc_idx: int) -> None:
        # 0. Initial setup

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful()

        all_bands_state = self.all_bands_proxy.read_attribute("State")
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_failure("test_parameters/configure_scan_invalid_2.json")

        assert_that(self.event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=self.all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.IDLE,
        )

        # 3. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful()
    
    #@pytest.mark.dev
    @pytest.mark.parametrize("fhs_vcc_idx", [1], ids=lambda i: f"fhs_vcc_idx={i}")
    def test_scan_sequence_commands_out_of_order_error(self, fhs_vcc_idx: int) -> None:
        # 0. Initial setup

        # Ensure emulators are reset before starting
        self.reset_emulators_and_assert_successful()

        all_bands_state = self.all_bands_proxy.read_attribute("State")
        all_bands_adminMode = self.all_bands_proxy.read_attribute("adminMode")

        self.logger.debug(f"allbands initial OpState: {all_bands_state}")
        self.logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.ONLINE)

        # 2. Run ConfigureScan()

        self.run_configure_scan_and_assert_success("test_parameters/configure_scan_valid_1.json")

        # 3. Run Scan()

        self.run_scan_and_assert_success()

        # 4. Run ConfigureScan() again (incorrect)

        self.run_configure_scan_and_assert_failure("test_parameters/configure_scan_valid_2.json")
        
        # 5. Run EndScan()

        self.run_end_scan_and_assert_success()

        # 6. Run GoToIdle()

        self.run_go_to_idle_and_assert_success()

        # 7. Set AdminMode.OFFLINE

        self.set_admin_mode_and_assert_change_events_occurred(AdminMode.OFFLINE)

        self.reset_emulators_and_assert_successful()
