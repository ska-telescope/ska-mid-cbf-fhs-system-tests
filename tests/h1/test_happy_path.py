import json

import pytest
from assertpy import assert_that
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState


@pytest.mark.nightly
class TestHappyPath:

    @pytest.fixture(scope="function")
    def event_tracer(
        self,
        all_bands_fqdn,
        eth_fqdn,
        pv_fqdn,
        wib_fqdn,
        device_idx,
    ) -> TangoEventTracer:
        tracer = TangoEventTracer()

        tracer.subscribe_event(all_bands_fqdn, "longRunningCommandResult")
        tracer.subscribe_event(all_bands_fqdn, "adminMode")
        tracer.subscribe_event(all_bands_fqdn, "state")
        tracer.subscribe_event(all_bands_fqdn, "obsState")

        tracer.subscribe_event(eth_fqdn, "obsState")
        tracer.subscribe_event(pv_fqdn, "obsState")
        tracer.subscribe_event(wib_fqdn, "obsState")

        return tracer

    @pytest.fixture(autouse=True)
    def reset_all_bands(self, all_bands_proxy, device_idx):
        all_bands_proxy.command_read_write("Init")

    @pytest.mark.parametrize("device_idx", [1, 2, 3, 4, 5, 6])
    def test_happy_path(
        self,
        logger,
        all_bands_fqdn,
        eth_fqdn,
        pv_fqdn,
        wib_fqdn,
        all_bands_proxy,
        eth_proxy,
        pv_proxy,
        wib_proxy,
        wfs_proxy,
        vcc_123_proxy,
        fss_proxy,
        event_tracer,
        device_idx,
    ):
        # 0. Initial setup

        all_bands_state = all_bands_proxy.read_attribute("State")
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        logger.debug(f"allbands initial OpState: {all_bands_state}")
        logger.debug(f"allbands initial AdminMode: {all_bands_adminMode}")

        # 1. Set AdminMode.ONLINE

        all_bands_proxy.write_attribute("adminMode", AdminMode.ONLINE)
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")
        all_bands_opState = all_bands_proxy.read_attribute("State")
        # Expose CommunicationState?

        logger.debug(f"allbands AdminMode after setting to ONLINE: {all_bands_adminMode}")
        logger.debug(f"allbands OpState after setting to ONLINE: {all_bands_opState}")
        assert all_bands_adminMode == AdminMode.ONLINE
        assert all_bands_opState == DevState.ON

        # 2. Run ConfigureScan()

        with open("test_parameters/configure_scan.json", "r") as configure_scan_file:
            configure_scan_data = configure_scan_file.read()
        assert len(configure_scan_data) > 0
        configure_scan_data_dict = json.loads(configure_scan_data)

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        all_bands_frequencyBand = all_bands_proxy.read_attribute("frequencyBand")
        all_bands_frequencyBandOffset = all_bands_proxy.read_attribute("frequencyBandOffset")
        vcc_123_status = vcc_123_proxy.command_read_write("GetStatus", False)
        wfs_status = json.loads(wfs_proxy.command_read_write("GetStatus", False)[1][0])
        # TODO: fix FSS emulator eventually
        # fss_status = json.loads(fss_proxy.command_read_write("GetStatus", False)[1][0])

        logger.debug(f"allbands ObsState before ConfigureScan: {all_bands_obsState}")
        logger.debug(f"allbands frequencyBand before ConfigureScan: {all_bands_frequencyBand}")
        logger.debug(f"allbands frequencyBandOffset before ConfigureScan: {all_bands_frequencyBandOffset}")
        logger.debug(f"vcc status before ConfigureScan: {vcc_123_status}")
        logger.debug(f"wfs status before ConfigureScan: {wfs_status}")
        # TODO: fix FSS emulator eventually
        # logger.debug(f'fss status before ConfigureScan: {fss_status}')

        configure_scan_result = all_bands_proxy.command_read_write("ConfigureScan", configure_scan_data)
        logger.debug(f"configure scan result: {configure_scan_result[1][0]}")

        assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="obsState",
            attribute_value=ObsState.CONFIGURING,
        )

        assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{configure_scan_result[1][0]}",
                '[0, "ConfigureScan completed OK"]',
            ),
        )

        assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
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

        logger.debug(f"allbands ObsState after ConfigureScan: {all_bands_obsState}")
        logger.debug(f"allbands frequencyBand after ConfigureScan: {all_bands_frequencyBand}")
        logger.debug(f"allbands frequencyBandOffset after ConfigureScan: {all_bands_frequencyBandOffset}")
        logger.debug(f"vcc status after ConfigureScan: {vcc_123_status}")
        logger.debug(f"wfs status after ConfigureScan: {wfs_status}")
        logger.debug(f"fss status after ConfigureScan: {fss_status}")

        expected_frequency_band = 1
        expected_frequency_band_offset = [
            configure_scan_data_dict.get("frequency_band_offset_stream_1"),
            configure_scan_data_dict.get("frequency_band_offset_stream_2"),
        ]

        assert all_bands_frequencyBand == expected_frequency_band
        assert len(all_bands_frequencyBandOffset) == 2
        assert all_bands_frequencyBandOffset[0] == expected_frequency_band_offset[0]
        assert all_bands_frequencyBandOffset[1] == expected_frequency_band_offset[1]

        # expected_sample_rate = configure_scan_data_dict.get("dish_sample_rate")
        expected_gains = configure_scan_data_dict.get("vcc_gain")
        expected_shift_frequency = expected_frequency_band_offset[0]
        expected_band_select = expected_frequency_band + 1

        # assert vcc_123_status.get("sample_rate") == expected_sample_rate
        vcc_123_gains = vcc_123_status.get("gains")
        assert all(expected_gains[i] == pytest.approx(vcc_123_gains[i].get("gain")) for i in range(len(expected_gains)))
        assert wfs_status.get("shift_frequency") == expected_shift_frequency
        assert fss_status.get("band_select") == expected_band_select

        # 3. Run Scan()

        eth_obsState = eth_proxy.read_attribute("obsState")
        pv_obsState = pv_proxy.read_attribute("obsState")
        wib_obsState = wib_proxy.read_attribute("obsState")

        logger.debug(f"Ethernet obsState before Scan: {eth_obsState}")
        logger.debug(f"Packet Validation obsState before Scan: {pv_obsState}")
        logger.debug(f"WIB obsState before Scan: {wib_obsState}")

        scan_result = all_bands_proxy.command_read_write("Scan", 0)

        assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{scan_result[1][0]}",
                '[0, "Scan completed OK"]',
            ),
        )

        for fqdn in [all_bands_fqdn, eth_fqdn, pv_fqdn, wib_fqdn]:
            assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
            )

        all_bands_opState = all_bands_proxy.read_attribute("State")
        assert all_bands_opState == DevState.ON

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        eth_obsState = eth_proxy.read_attribute("obsState")
        pv_obsState = pv_proxy.read_attribute("obsState")
        wib_obsState = wib_proxy.read_attribute("obsState")

        logger.debug(f"allbands obsState after Scan: {all_bands_obsState}")
        logger.debug(f"Ethernet obsState after Scan: {eth_obsState}")
        logger.debug(f"Packet Validation obsState after Scan: {pv_obsState}")
        logger.debug(f"WIB obsState after Scan: {wib_obsState}")

        # 4. Run EndScan()

        end_scan_result = all_bands_proxy.command_read_write("EndScan")

        assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
            device_name=all_bands_fqdn,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{end_scan_result[1][0]}",
                '[0, "EndScan completed OK"]',
            ),
        )

        for fqdn in [all_bands_fqdn, eth_fqdn, pv_fqdn, wib_fqdn]:
            assert_that(event_tracer).within_timeout(60).has_change_event_occurred(
                device_name=fqdn,
                attribute_name="obsState",
                attribute_value=ObsState.READY,
            )

        all_bands_obsState = all_bands_proxy.read_attribute("obsState")
        logger.debug(f"allbands obsState after EndScan: {all_bands_obsState}")

        eth_obsState = eth_proxy.read_attribute("obsState")
        pv_obsState = pv_proxy.read_attribute("obsState")
        wib_obsState = wib_proxy.read_attribute("obsState")

        logger.debug(f"Ethernet obsState after EndScan: {eth_obsState}")
        logger.debug(f"Packet Validation obsState after EndScan: {pv_obsState}")
        logger.debug(f"WIB obsState after EndScan: {wib_obsState}")

        # 5. Run GoToIdle()

        # go_to_idle_result = all_bands_proxy.command_read_write("GoToIdle")

        # 6. Set AdminMode.OFFLINE

        all_bands_proxy.write_attribute("adminMode", AdminMode.OFFLINE)
        all_bands_adminMode = all_bands_proxy.read_attribute("adminMode")

        assert all_bands_adminMode == AdminMode.OFFLINE
