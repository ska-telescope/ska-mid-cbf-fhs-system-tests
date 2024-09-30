import sys
from typing import Any

from tango import DevFailed, DeviceProxy


class PyTangoClientWrapper:
    """Wrapper class for utilizing Tango.DeviceProxy"""

    def __init__(self):
        self.device_proxy = None
        self.timeout_ms = 3000  # Default Tango timeout

    def create_tango_client(self, dev_name: str):
        """
        Creates a device proxy to the specified device.

        :param dev_name: Device FQDN to connect to
        """
        try:
            self.device_proxy = DeviceProxy(dev_name)
            print(f"Device State : {self.device_proxy.state()}")
            print(f"Device Status: {self.device_proxy.status()}")
            print(f"dev_name = {dev_name}")

        except DevFailed as e:
            print(f"Error on DeviceProxy: {e}")
            self.clear_all()
            sys.exit(str(e))

    def clear_all(self):
        """
        Reset all class variables to the default setting.
        """
        self.timeout_ms = 3000
        if self.device_proxy is not None:
            self.device_proxy = None

    def set_timeout(self, timeout: int):
        """
        Set the timeout of the DeviceProxy connection.

        :param timeout_ms: Timeout in seconds
        """
        try:
            self.timeout_ms = timeout * 1000
            self.device_proxy.set_timeout_millis(self.timeout_ms)
        except DevFailed as e:
            print(str(e))

    def write_attribute(self, attr_name: str, value: Any):
        """
        Write to an attribute.

        :param attr_name: Attribute to write to
        :param value: Value to write
        """
        try:
            self.device_proxy.write_attribute(attr_name, value)
        except DevFailed as e:
            print(str(e))

    def read_attribute(self, attr_name: str) -> Any:
        """
        Read from an attribute.

        :param attr_name: Attribute to read from
        :returns: Attribute value or None if an exception occurred
        """
        try:
            attr_read = self.device_proxy.read_attribute(attr_name)
            return attr_read.value
        except DevFailed as e:
            print(str(e))
            return None

    def command_read_write(self, command_name: str, *args) -> Any:
        """
        Send a command.

        :param command_name: Name of the command
        :param args: Input arguments
        :returns: Command result or None if an exception occurred
        """
        try:
            return self.device_proxy.command_inout(command_name, *args)
        except DevFailed as e:
            print(str(e))
            return None

    def get_property(self, property_name: str) -> Any:
        """
        Get a (list) property(ies) for a device.

        :param property_name: Name of the property
        :returns: Property(ies) values or None if an exception occurred
        """
        try:
            return self.device_proxy.get_property(property_name)
        except DevFailed as e:
            print(str(e))
            return None
