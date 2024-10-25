import time
from enum import Enum
from typing import Any

import requests
from pytango_client_wrapper import PyTangoClientWrapper


class DeviceKey(Enum):
    """Enum of device names for mapping to device FQDNs/etc."""

    ALL_BANDS = "all_bands"
    VCC_123 = "vcc_123"
    FREQ_SLICE_SELECTION = "frequency_slice_selection"
    ETHERNET = "ethernet"
    PACKET_VALIDATION = "packet_validation"
    WIDEBAND_FREQ_SHIFTER = "wideband_frequency_shifter"
    WIDEBAND_INPUT_BUFFER = "widebend_input_buffer"


class EmulatorIPBlockId(Enum):
    """Enum of IP block IDs."""

    ETHERNET_200G = "ethernet_200g"
    PACKET_VALIDATION = "packet_validation"
    WIDEBAND_INPUT_BUFFER = "wideband_input_buffer"
    WIDEBAND_FREQ_SHIFTER = "wideband_frequency_shifter"
    VCC_123 = "b123vcc"
    FREQ_SLICE_SELECTION = "fs_selection_26_2_1"


fqdn_map = {
    DeviceKey.ALL_BANDS: "fhs/vcc-all-bands/",
    DeviceKey.VCC_123: "fhs/vcc/",
    DeviceKey.FREQ_SLICE_SELECTION: "fhs/fss/",
    DeviceKey.ETHERNET: "fhs/mac200/",
    DeviceKey.PACKET_VALIDATION: "fhs/packetvalidation/",
    DeviceKey.WIDEBAND_FREQ_SHIFTER: "fhs/wfs/",
    DeviceKey.WIDEBAND_INPUT_BUFFER: "fhs/wib/",
}


def get_fqdn(fhs_vcc_idx: int, fqdn_key: DeviceKey) -> str:
    """Get the FQDN for a given device name/key and index."""
    mapped_idx = str(fhs_vcc_idx).zfill(3)
    return fqdn_map[fqdn_key] + mapped_idx


def create_proxy(fhs_vcc_idx: int, fqdn_key: DeviceKey) -> PyTangoClientWrapper:
    """Create and return a proxy wrapper for a given device name/key and index."""
    proxy = PyTangoClientWrapper()
    proxy.create_tango_client(get_fqdn(fhs_vcc_idx, fqdn_key))
    return proxy


class EmulatorAPIService:
    """Service containing methods for interacting with the emulator APIs."""

    @staticmethod
    def get(base_url: str, ip_block: EmulatorIPBlockId | None = None, route: str = "state", param_string: str = "") -> Any:
        """Send a GET request to the specified emulator URL, IP block ID (if specified) and route,
        and return the response contents.
        """
        ip_string = f"/{ip_block.value}" if ip_block is not None else ""
        full_url = f"http://{base_url}{ip_string}/{route}/{param_string}"
        resp = requests.get(full_url)
        if resp.status_code >= 300:
            raise Exception(f"GET: {full_url} failed: {resp.content}")
        return resp.json()

    @staticmethod
    def post(base_url: str, ip_block: EmulatorIPBlockId | None = None, route: str = "start", param_string: str = "", body: dict | str = {}) -> Any:
        """Send a POST request to the specified emulator URL, IP block ID (if specified),
        route, and body, and return the response contents.
        """
        ip_string = f"/{ip_block.value}" if ip_block is not None else ""
        full_url = f"http://{base_url}{ip_string}/{route}/{param_string}"
        resp = requests.post(full_url, json=body)
        if resp.status_code >= 300:
            raise Exception(f"POST: {full_url} failed: {resp.content}")
        return resp.json()

    @staticmethod
    def wait_for_state(base_url: str, ip_block: EmulatorIPBlockId | None, state: str, poll_interval_sec: int = 1, timeout_sec: int = 60) -> tuple[str, bool]:
        """Poll the specified emulator/ip block state until it matches
        the specified destination state. Returns a 2-tuple containing the last retrieved state
        (will match the destination state unless timed out),
        and whether the retrieval was successful or not.
        """
        start_time = time.time()
        while True:
            got_state = EmulatorAPIService.get(base_url, ip_block, "state")
            if got_state.get("current_state") == state:
                return got_state, True
            if time.time() > start_time + timeout_sec:
                return got_state, False
            time.sleep(poll_interval_sec)
