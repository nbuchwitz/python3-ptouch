# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Connection classes for Brother P-touch printers."""

import socket
from abc import ABC, abstractmethod
from typing import Any

import usb.core
import usb.util

from .config import USB_VENDOR_ID


class Connection(ABC):
    """Abstract base class for printer connections."""

    @abstractmethod
    def write(self, payload: bytes) -> None:
        """Write data to the printer.

        Parameters
        ----------
        payload : bytes
            Bytes to send to the printer.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the connection and release resources."""

    def read(self, num_bytes: int = 1024) -> bytes:
        """Read data from the printer (optional, not all connections support this).

        Parameters
        ----------
        num_bytes : int, default 1024
            Maximum number of bytes to read.

        Returns
        -------
        bytes
            Bytes received from the printer.

        Raises
        ------
        NotImplementedError
            If the connection does not support reading.
        """
        raise NotImplementedError("This connection does not support reading")

    def __del__(self) -> None:
        """Clean up connection on garbage collection."""
        self.close()


class ConnectionUSB(Connection):
    """USB connection for Brother label printers.

    Parameters
    ----------
    product_id : int
        USB product ID of the printer.

    Raises
    ------
    ValueError
        If the printer device is not found or endpoints are missing.
    """

    def __init__(self, product_id: int) -> None:
        self._device: Any = usb.core.find(idVendor=USB_VENDOR_ID, idProduct=product_id)
        if self._device is None:
            raise ValueError("Printer device not found.")

        self._kernel_driver_detached = False
        interface = self._device[0].interfaces()[0]
        if self._device.is_kernel_driver_active(interface.bInterfaceNumber):
            self._device.detach_kernel_driver(interface.bInterfaceNumber)
            self._kernel_driver_detached = True

        self._device.set_configuration()

        cfg = self._device.get_active_configuration()
        intf = usb.util.find_descriptor(cfg, bInterfaceClass=7)
        assert intf is not None

        def match_endpoint_in(endpoint: Any) -> bool:
            return usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN

        def match_endpoint_out(endpoint: Any) -> bool:
            return usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_OUT

        self._ep_in: Any = usb.util.find_descriptor(intf, custom_match=match_endpoint_in)
        self._ep_out: Any = usb.util.find_descriptor(intf, custom_match=match_endpoint_out)

        if self._ep_in is None or self._ep_out is None:
            raise ValueError("USB endpoints not found.")

    def write(self, payload: bytes) -> None:
        """Write data to the printer via USB."""
        self._ep_out.write(payload, len(payload))

    def close(self) -> None:
        """Close USB connection and reattach kernel driver if needed."""
        if self._device is not None:
            usb.util.dispose_resources(self._device)
            if self._kernel_driver_detached:
                try:
                    self._device.attach_kernel_driver(0)
                except usb.core.USBError:
                    pass  # Ignore errors when reattaching kernel driver
            self._device = None


class ConnectionNetwork(Connection):
    """Network (TCP/IP) connection for Brother label printers.

    Parameters
    ----------
    host : str
        Hostname or IP address of the printer.
    port : int, default 9100
        TCP port number for raw printing.
    """

    def __init__(self, host: str, port: int = 9100) -> None:
        self.host = host
        self.port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Disable Nagle's algorithm to send packets immediately
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket.connect((self.host, self.port))
        self._socket.setblocking(True)

    def write(self, payload: bytes) -> None:
        """Write data to the printer via network."""
        self._socket.sendall(payload)

    def read(self, num_bytes: int = 1024) -> bytes:
        """Read data from the printer via network."""
        return self._socket.recv(num_bytes)

    def close(self) -> None:
        """Close the network connection."""
        self._socket.close()
