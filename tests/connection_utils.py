import time
from enum import Enum
from typing import Any

import requests
from pytango_client_wrapper import PyTangoClientWrapper


class DeviceKey(Enum):
    ALL_BANDS = "all_bands"
    VCC_123 = "vcc_123"
    FREQ_SLICE_SELECTION = "frequency_slice_selection"
    ETHERNET = "ethernet"
    PACKET_VALIDATION = "packet_validation"
    WIDEBAND_FREQ_SHIFTER = "wideband_frequency_shifter"
    WIDEBAND_INPUT_BUFFER = "widebend_input_buffer"


class EmulatorIPBlockId(Enum):
    ETHERNET_200G = "ethernet_200g"
    PACKET_VALIDATION = "packet_validation"
    WIDEBAND_INPUT_BUFFER = "wideband_input_buffer"
    WIDEBAND_FREQ_SHIFTER = "wideband_frequency_shifter"
    VCC_123 = "b123vcc"
    FREQ_SLICE_SELECTION = "fs_selection_26_2_1"


fqdn_map = {
    DeviceKey.ALL_BANDS: "fhs/vcc-all-bands/",
    DeviceKey.VCC_123: "fhs/vcc/",
    DeviceKey.FREQ_SLICE_SELECTION: "fhs/frequency-slice-selection/",
    DeviceKey.ETHERNET: "fhs/mac200/",
    DeviceKey.PACKET_VALIDATION: "fhs/packetvalidation/",
    DeviceKey.WIDEBAND_FREQ_SHIFTER: "fhs/wfs/",
    DeviceKey.WIDEBAND_INPUT_BUFFER: "fhs/wib/",
}


def get_fqdn(device_idx: int, fqdn_key: DeviceKey) -> str:
    mapped_idx = str(device_idx - 1).zfill(3)
    return fqdn_map[fqdn_key] + mapped_idx


def create_proxy(device_idx: int, fqdn_key: DeviceKey) -> PyTangoClientWrapper:
    proxy = PyTangoClientWrapper()
    proxy.create_tango_client(get_fqdn(device_idx, fqdn_key))
    return proxy


class EmulatorAPIService:
    @staticmethod
    def get(base_url: str, ip_block: EmulatorIPBlockId | None = None, route: str = "state", param_string: str = "") -> Any:
        ip_string = f"/{ip_block.value}" if ip_block is not None else ""
        full_url = f"http://{base_url}{ip_string}/{route}/{param_string}"
        resp = requests.get(full_url)
        if resp.status_code >= 300:
            raise Exception(f"GET: {full_url} failed: {resp.content}")
        return resp.json()

    @staticmethod
    def post(base_url: str, ip_block: EmulatorIPBlockId | None = None, route: str = "state", param_string: str = "", body: dict | str = {}) -> Any:
        ip_string = f"/{ip_block.value}" if ip_block is not None else ""
        full_url = f"http://{base_url}{ip_string}/{route}/{param_string}"
        resp = requests.post(full_url, json=body)
        if resp.status_code >= 300:
            raise Exception(f"POST: {full_url} failed: {resp.content}")
        return resp.json()

    @staticmethod
    def wait_for_state(base_url: str, ip_block: EmulatorIPBlockId | None, state: str, poll_interval_sec: int = 1, timeout_sec: int = 60) -> tuple[str, bool]:
        start_time = time.time()
        while True:
            got_state = EmulatorAPIService.get(base_url, ip_block, "state")
            if got_state.get("current_state") == state:
                return got_state, True
            if time.time() > start_time + timeout_sec:
                return got_state, False
            time.sleep(poll_interval_sec)
