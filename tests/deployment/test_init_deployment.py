from __future__ import annotations

import pytest
from ska_control_model import ResultCode
from pytango_client_wrapper import PyTangoClientWrapper
from tango import DevState
import requests

@pytest.mark.nightly
class TestInitDeployment():
    
    def test_device_server_deployment(self: TestInitDeployment):
        mac200_000_proxy = PyTangoClientWrapper()
        vcc_000_proxy = PyTangoClientWrapper()
        fss_000_proxy = PyTangoClientWrapper()
        wfs_000_proxy = PyTangoClientWrapper()
        wib_000_proxy = PyTangoClientWrapper()
        pv_000_proxy = PyTangoClientWrapper()
        
        mac200_000_proxy.create_tango_client('fhs/mac200/000')
        vcc_000_proxy.create_tango_client('fhs/vcc/000')
        fss_000_proxy.create_tango_client('fhs/frequency-slice-selection/000')
        wfs_000_proxy.create_tango_client('fhs/wfs/000')
        wib_000_proxy.create_tango_client('fhs/wib/000')
        pv_000_proxy.create_tango_client('fhs/packetvalidation/000')

        mac200_000_state = mac200_000_proxy.read_attribute('State')
        vcc_000_state = vcc_000_proxy.read_attribute('State')
        fss_000_state = fss_000_proxy.read_attribute('State')
        wfs_000_state = wfs_000_proxy.read_attribute('State')
        wib_000_state = wib_000_proxy.read_attribute('State')
        pv_000_state = pv_000_proxy.read_attribute('State')
        
        print(f'mac200 state {mac200_000_state}')
        print(f'vcc state {vcc_000_state}')
        print(f'fss state {fss_000_state}')
        print(f'wfs state {wfs_000_state}')
        print(f'wib state {wib_000_state}')
        print(f'pv state {pv_000_state}')
        
        assert mac200_000_state == DevState.ON
        assert vcc_000_state == DevState.ON
        assert fss_000_state == DevState.ON
        assert wfs_000_state == DevState.ON
        assert wib_000_state == DevState.ON
        assert pv_000_state == DevState.ON
        
    def test_init_emulators(self: TestInitDeployment, namespace):
        response: requests.Response = requests.get(f'http://fhs-vcc-emulator-1.{namespace}.svc.cluster.local:5001/state', )
        emulator1_json = response.json()
        
        assert emulator1_json['current_state'] == 'RUNNING'
        
        
    def test_device_servers_to_emulator_connection(self: TestInitDeployment, namespace):
        
        mac200_000_proxy = PyTangoClientWrapper()
        vcc_000_proxy = PyTangoClientWrapper()
        fss_000_proxy = PyTangoClientWrapper()
        wfs_000_proxy = PyTangoClientWrapper()
        wib_000_proxy = PyTangoClientWrapper()
        pv_000_proxy = PyTangoClientWrapper()
        
        mac200_000_proxy.create_tango_client('fhs/mac200/000')
        vcc_000_proxy.create_tango_client('fhs/vcc/000')
        fss_000_proxy.create_tango_client('fhs/frequency-slice-selection/000')
        wfs_000_proxy.create_tango_client('fhs/wfs/000')
        wib_000_proxy.create_tango_client('fhs/wib/000')
        pv_000_proxy.create_tango_client('fhs/packetvalidation/000')
        
        mac200_status = mac200_000_proxy.command_read_write("GetStatus")
        vcc_status = vcc_000_proxy.command_read_write("GetStatus")
        fss_status = fss_000_proxy.command_read_write("GetStatus")
        wfs_status = wfs_000_proxy.command_read_write("GetStatus")
        wib_status = wib_000_proxy.command_read_write("GetStatus")
        pv_status = pv_000_proxy.command_read_write("GetStatus")
        
        print(f'......Mac200Stats: {mac200_status}......')
        
        assert mac200_status[0] is ResultCode.OK
        assert vcc_status[0] is ResultCode.OK
        assert fss_status[0] is ResultCode.OK
        assert fss_status[0] is ResultCode.OK
        assert wfs_status[0] is ResultCode.OK
        assert wib_status[0] is ResultCode.OK
        assert pv_status[0] is ResultCode.OK