# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Connection classes for Brother P-touch printers."""

from __future__ import annotations

import errno
import socket
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import usb.core
import usb.util

if TYPE_CHECKING:
    from .printer import LabelPrinter

# USB vendor ID for Brother Industries
USB_VENDOR_ID = 0x04F9


class PrinterConnectionError(Exception):
    """Exception raised when connection to printer fails.

    Parameters
    ----------
    message : str
        Human-readable error message.
    original_error : Exception, optional
        The underlying exception that caused this error.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class Connection(ABC):
    """Abstract base class for printer connections."""

    @abstractmethod
    def connect(self, printer: LabelPrinter) -> None:
        """Establish the connection to the printer.

        Parameters
        ----------
        printer : LabelPrinter
            The printer instance that will use this connection.
        """

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

    The actual USB connection is established when connect() is called by the printer.
    The printer class must define a USB_PRODUCT_ID class attribute.

    Raises
    ------
    PrinterConnectionError
        If the printer device is not found, endpoints are missing, or USB access fails.
    """

    def __init__(self) -> None:
        self._device: Any = None
        self._ep_in: Any = None
        self._ep_out: Any = None
        self._kernel_driver_detached = False

    def connect(self, printer: LabelPrinter) -> None:
        """Establish USB connection to the printer.

        Parameters
        ----------
        printer : LabelPrinter
            The printer instance. Must have USB_PRODUCT_ID class attribute.

        Raises
        ------
        PrinterConnectionError
            If USB_PRODUCT_ID is not defined on the printer class,
            the device is not found, or USB access fails.
        """
        product_id = getattr(printer, "USB_PRODUCT_ID", None)
        if product_id is None:
            raise PrinterConnectionError(
                f"{printer.__class__.__name__} does not define USB_PRODUCT_ID. "
                "USB connection requires a printer class with USB_PRODUCT_ID attribute."
            )

        self._device = usb.core.find(idVendor=USB_VENDOR_ID, idProduct=product_id)
        if self._device is None:
            raise PrinterConnectionError(
                f"USB printer with product ID 0x{product_id:04X} not found. "
                "Check if the printer is connected and powered on."
            )

        try:
            interface = self._device[0].interfaces()[0]
            if self._device.is_kernel_driver_active(interface.bInterfaceNumber):
                self._device.detach_kernel_driver(interface.bInterfaceNumber)
                self._kernel_driver_detached = True

            self._device.set_configuration()
        except usb.core.USBError as e:
            if e.errno == errno.EACCES:
                raise PrinterConnectionError(
                    "Permission denied accessing USB printer. "
                    "Try running with sudo or configure udev rules.",
                    original_error=e,
                ) from e
            raise PrinterConnectionError(
                f"Failed to initialize USB printer: {e}",
                original_error=e,
            ) from e

        cfg = self._device.get_active_configuration()
        intf = usb.util.find_descriptor(cfg, bInterfaceClass=7)
        assert intf is not None

        def match_endpoint_in(endpoint: Any) -> bool:
            return usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN

        def match_endpoint_out(endpoint: Any) -> bool:
            return usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_OUT

        self._ep_in = usb.util.find_descriptor(intf, custom_match=match_endpoint_in)
        self._ep_out = usb.util.find_descriptor(intf, custom_match=match_endpoint_out)

        if self._ep_in is None or self._ep_out is None:
            raise PrinterConnectionError(
                "USB endpoints not found. The device may not be a supported printer."
            )

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

    The actual socket connection is established when connect() is called by the printer.

    Parameters
    ----------
    host : str
        Hostname or IP address of the printer.
    port : int, default 9100
        TCP port number for raw printing.
    timeout : float, default 5.0
        Connection timeout in seconds. Also used for read/write operations.
    """

    def __init__(self, host: str, port: int = 9100, timeout: float = 5.0) -> None:
        self._socket: socket.socket | None = None
        self.host = host
        self.port = port
        self.timeout = timeout

    def connect(self, printer: LabelPrinter) -> None:
        """Establish network connection to the printer.

        Parameters
        ----------
        printer : LabelPrinter
            The printer instance (not used for network connections).

        Raises
        ------
        PrinterConnectionError
            If the printer cannot be reached or connection fails.
        """
        del printer  # unused for network connections

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Disable Nagle's algorithm to send packets immediately
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket.settimeout(self.timeout)

        try:
            self._socket.connect((self.host, self.port))
        except socket.timeout as e:
            self._socket.close()
            self._socket = None
            raise PrinterConnectionError(
                f"Connection to printer at {self.host}:{self.port} timed out after {self.timeout}s",
                original_error=e,
            ) from e
        except ConnectionRefusedError as e:
            self._socket.close()
            self._socket = None
            raise PrinterConnectionError(
                f"Connection refused by printer at {self.host}:{self.port}. "
                "Check if the printer is powered on and accepts network connections.",
                original_error=e,
            ) from e
        except socket.gaierror as e:
            self._socket.close()
            self._socket = None
            raise PrinterConnectionError(
                f"Cannot resolve hostname '{self.host}'. "
                "Check if the hostname or IP address is correct.",
                original_error=e,
            ) from e
        except OSError as e:
            self._socket.close()
            self._socket = None
            raise PrinterConnectionError(
                f"Failed to connect to printer at {self.host}:{self.port}: {e}",
                original_error=e,
            ) from e

    def write(self, payload: bytes) -> None:
        """Write data to the printer via network.

        Raises
        ------
        PrinterConnectionError
            If writing to the printer fails or times out.
        """
        if self._socket is None:
            raise PrinterConnectionError("Not connected to printer")

        try:
            self._socket.sendall(payload)
        except socket.timeout as e:
            raise PrinterConnectionError(
                f"Write to printer at {self.host}:{self.port} timed out",
                original_error=e,
            ) from e
        except (BrokenPipeError, ConnectionResetError) as e:
            raise PrinterConnectionError(
                f"Connection to printer at {self.host}:{self.port} was lost",
                original_error=e,
            ) from e
        except OSError as e:
            raise PrinterConnectionError(
                f"Failed to write to printer at {self.host}:{self.port}: {e}",
                original_error=e,
            ) from e

    def read(self, num_bytes: int = 1024) -> bytes:
        """Read data from the printer via network.

        Raises
        ------
        PrinterConnectionError
            If reading from the printer fails or times out.
        """
        if self._socket is None:
            raise PrinterConnectionError("Not connected to printer")

        try:
            return self._socket.recv(num_bytes)
        except socket.timeout as e:
            raise PrinterConnectionError(
                f"Read from printer at {self.host}:{self.port} timed out",
                original_error=e,
            ) from e
        except (BrokenPipeError, ConnectionResetError) as e:
            raise PrinterConnectionError(
                f"Connection to printer at {self.host}:{self.port} was lost",
                original_error=e,
            ) from e
        except OSError as e:
            raise PrinterConnectionError(
                f"Failed to read from printer at {self.host}:{self.port}: {e}",
                original_error=e,
            ) from e

    def close(self) -> None:
        """Close the network connection."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None
