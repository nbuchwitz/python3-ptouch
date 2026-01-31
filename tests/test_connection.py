# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.connection module."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from ptouch.connection import ConnectionNetwork, ConnectionUSB, PrinterConnectionError


class MockPrinter:
    """Mock printer for testing USB connections."""

    USB_PRODUCT_ID = 0x1234


class MockPrinterNoUSB:
    """Mock printer without USB_PRODUCT_ID for testing error case."""

    pass


class TestPrinterConnectionError:
    """Test PrinterConnectionError exception."""

    def test_exception_message(self) -> None:
        """Test that exception stores message correctly."""
        error = PrinterConnectionError("Test error message")
        assert str(error) == "Test error message"
        assert error.original_error is None

    def test_exception_with_original_error(self) -> None:
        """Test that exception stores original error."""
        original = ValueError("Original error")
        error = PrinterConnectionError("Wrapped error", original_error=original)
        assert str(error) == "Wrapped error"
        assert error.original_error is original

    def test_exception_is_importable_from_package(self) -> None:
        """Test that PrinterConnectionError can be imported from ptouch."""
        from ptouch import PrinterConnectionError as ImportedError

        assert ImportedError is PrinterConnectionError


class TestConnectionUSBInit:
    """Test ConnectionUSB initialization."""

    def test_usb_connection_init_no_args(self) -> None:
        """Test that ConnectionUSB can be created without arguments."""
        conn = ConnectionUSB()
        assert conn._device is None
        assert conn._ep_in is None
        assert conn._ep_out is None

    def test_usb_connect_requires_product_id(self) -> None:
        """Test that connect() raises error if printer has no USB_PRODUCT_ID."""
        conn = ConnectionUSB()
        with pytest.raises(PrinterConnectionError) as exc_info:
            conn.connect(MockPrinterNoUSB())  # type: ignore[arg-type]

        assert "USB_PRODUCT_ID" in str(exc_info.value)

    def test_usb_connect_with_mock_printer(self) -> None:
        """Test that connect() uses printer's USB_PRODUCT_ID."""
        with patch("usb.core.find") as mock_find:
            mock_device = MagicMock()
            mock_find.return_value = mock_device
            mock_device.is_kernel_driver_active.return_value = False

            mock_intf = MagicMock()
            mock_intf.bInterfaceClass = 7

            mock_cfg = MagicMock()
            mock_device.get_active_configuration.return_value = mock_cfg

            with patch("usb.util.find_descriptor") as mock_find_desc:
                mock_ep = MagicMock()
                mock_find_desc.return_value = mock_ep

                conn = ConnectionUSB()
                conn.connect(MockPrinter())  # type: ignore[arg-type]

                # Should have called usb.core.find with the product ID from MockPrinter
                mock_find.assert_called_once()
                call_kwargs = mock_find.call_args[1]
                assert call_kwargs["idProduct"] == 0x1234


class TestConnectionNetworkInit:
    """Test ConnectionNetwork initialization and connect()."""

    def test_network_init_stores_params(self) -> None:
        """Test that __init__ stores parameters without connecting."""
        conn = ConnectionNetwork("192.168.1.100", timeout=10.0)
        assert conn.host == "192.168.1.100"
        assert conn.port == 9100
        assert conn.timeout == 10.0
        assert conn._socket is None  # Not connected yet

    def test_default_timeout(self) -> None:
        """Test that default timeout is 5.0 seconds."""
        conn = ConnectionNetwork("192.168.1.100")
        assert conn.timeout == 5.0

    def test_connect_establishes_socket(self) -> None:
        """Test that connect() creates and configures socket."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            conn = ConnectionNetwork("192.168.1.100", timeout=10.0)
            conn.connect(MockPrinter())  # type: ignore[arg-type]

            mock_sock.settimeout.assert_called_with(10.0)
            mock_sock.connect.assert_called_once_with(("192.168.1.100", 9100))

    def test_connection_timeout_raises_printer_error(self) -> None:
        """Test that connection timeout raises PrinterConnectionError."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = socket.timeout("timed out")

            conn = ConnectionNetwork("192.168.1.100", timeout=5.0)
            with pytest.raises(PrinterConnectionError) as exc_info:
                conn.connect(MockPrinter())  # type: ignore[arg-type]

            assert "timed out" in str(exc_info.value)
            assert "192.168.1.100:9100" in str(exc_info.value)
            assert isinstance(exc_info.value.original_error, socket.timeout)
            mock_sock.close.assert_called_once()

    def test_connection_refused_raises_printer_error(self) -> None:
        """Test that connection refused raises PrinterConnectionError."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")

            conn = ConnectionNetwork("192.168.1.100")
            with pytest.raises(PrinterConnectionError) as exc_info:
                conn.connect(MockPrinter())  # type: ignore[arg-type]

            assert "refused" in str(exc_info.value).lower()
            assert "192.168.1.100:9100" in str(exc_info.value)
            assert isinstance(exc_info.value.original_error, ConnectionRefusedError)
            mock_sock.close.assert_called_once()

    def test_hostname_resolution_error_raises_printer_error(self) -> None:
        """Test that hostname resolution failure raises PrinterConnectionError."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = socket.gaierror(8, "Name not resolved")

            conn = ConnectionNetwork("invalid.hostname.local")
            with pytest.raises(PrinterConnectionError) as exc_info:
                conn.connect(MockPrinter())  # type: ignore[arg-type]

            assert "invalid.hostname.local" in str(exc_info.value)
            assert "resolve" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_error, socket.gaierror)
            mock_sock.close.assert_called_once()

    def test_generic_os_error_raises_printer_error(self) -> None:
        """Test that generic OSError raises PrinterConnectionError."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = OSError("Network unreachable")

            conn = ConnectionNetwork("192.168.1.100")
            with pytest.raises(PrinterConnectionError) as exc_info:
                conn.connect(MockPrinter())  # type: ignore[arg-type]

            assert "192.168.1.100:9100" in str(exc_info.value)
            assert isinstance(exc_info.value.original_error, OSError)
            mock_sock.close.assert_called_once()


class TestConnectionNetworkWrite:
    """Test ConnectionNetwork write method error handling."""

    @pytest.fixture
    def connected_network(self) -> ConnectionNetwork:
        """Create a ConnectionNetwork with mocked socket."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            conn = ConnectionNetwork("192.168.1.100")
            conn.connect(MockPrinter())  # type: ignore[arg-type]
            return conn

    def test_write_timeout_raises_printer_error(self, connected_network: ConnectionNetwork) -> None:
        """Test that write timeout raises PrinterConnectionError."""
        assert connected_network._socket is not None
        connected_network._socket.sendall.side_effect = socket.timeout("timed out")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "timed out" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, socket.timeout)

    def test_write_broken_pipe_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that broken pipe raises PrinterConnectionError."""
        assert connected_network._socket is not None
        connected_network._socket.sendall.side_effect = BrokenPipeError("Broken pipe")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, BrokenPipeError)

    def test_write_connection_reset_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that connection reset raises PrinterConnectionError."""
        assert connected_network._socket is not None
        connected_network._socket.sendall.side_effect = ConnectionResetError("Connection reset")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, ConnectionResetError)

    def test_write_not_connected_raises_printer_error(self) -> None:
        """Test that write before connect raises PrinterConnectionError."""
        conn = ConnectionNetwork("192.168.1.100")
        with pytest.raises(PrinterConnectionError) as exc_info:
            conn.write(b"test data")

        assert "Not connected" in str(exc_info.value)


class TestConnectionNetworkRead:
    """Test ConnectionNetwork read method error handling."""

    @pytest.fixture
    def connected_network(self) -> ConnectionNetwork:
        """Create a ConnectionNetwork with mocked socket."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            conn = ConnectionNetwork("192.168.1.100")
            conn.connect(MockPrinter())  # type: ignore[arg-type]
            return conn

    def test_read_timeout_raises_printer_error(self, connected_network: ConnectionNetwork) -> None:
        """Test that read timeout raises PrinterConnectionError."""
        assert connected_network._socket is not None
        connected_network._socket.recv.side_effect = socket.timeout("timed out")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.read()

        assert "timed out" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, socket.timeout)

    def test_read_broken_pipe_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that broken pipe raises PrinterConnectionError."""
        assert connected_network._socket is not None
        connected_network._socket.recv.side_effect = BrokenPipeError("Broken pipe")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.read()

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, BrokenPipeError)

    def test_read_not_connected_raises_printer_error(self) -> None:
        """Test that read before connect raises PrinterConnectionError."""
        conn = ConnectionNetwork("192.168.1.100")
        with pytest.raises(PrinterConnectionError) as exc_info:
            conn.read()

        assert "Not connected" in str(exc_info.value)
