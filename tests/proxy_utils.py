from pytango_client_wrapper import PyTangoClientWrapper

fqdn_map = {
    "all_bands": "fhs/vcc-all-bands/",
    "vcc_123": "fhs/vcc/",
    "fss": "fhs/frequency-slice-selection/",
    "ethernet": "fhs/mac200/",
    "pv": "fhs/packetvalidation/",
    "wfs": "fhs/wfs/",
    "wib": "fhs/wib/",
}


def get_fqdn(device_idx, fqdn_key):
    mapped_idx = str(device_idx - 1).zfill(3)
    return fqdn_map[fqdn_key] + mapped_idx


def create_proxy(device_idx, fqdn_key):
    proxy = PyTangoClientWrapper()
    proxy.create_tango_client(get_fqdn(device_idx, fqdn_key))
    return proxy
