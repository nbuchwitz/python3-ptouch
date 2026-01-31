# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.connection module."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from ptouch.connection import ConnectionNetwork, PrinterConnectionError


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


class TestConnectionNetworkInit:
    """Test ConnectionNetwork initialization and error handling."""

    def test_timeout_parameter_stored(self) -> None:
        """Test that timeout parameter is stored."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            conn = ConnectionNetwork("192.168.1.100", timeout=10.0)

            assert conn.timeout == 10.0
            mock_sock.settimeout.assert_called_with(10.0)

    def test_default_timeout(self) -> None:
        """Test that default timeout is 5.0 seconds."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            conn = ConnectionNetwork("192.168.1.100")

            assert conn.timeout == 5.0
            mock_sock.settimeout.assert_called_with(5.0)

    def test_connection_timeout_raises_printer_error(self) -> None:
        """Test that connection timeout raises PrinterConnectionError."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = socket.timeout("timed out")

            with pytest.raises(PrinterConnectionError) as exc_info:
                ConnectionNetwork("192.168.1.100", timeout=5.0)

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

            with pytest.raises(PrinterConnectionError) as exc_info:
                ConnectionNetwork("192.168.1.100")

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

            with pytest.raises(PrinterConnectionError) as exc_info:
                ConnectionNetwork("invalid.hostname.local")

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

            with pytest.raises(PrinterConnectionError) as exc_info:
                ConnectionNetwork("192.168.1.100")

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
            return conn

    def test_write_timeout_raises_printer_error(self, connected_network: ConnectionNetwork) -> None:
        """Test that write timeout raises PrinterConnectionError."""
        connected_network._socket.sendall.side_effect = socket.timeout("timed out")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "timed out" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, socket.timeout)

    def test_write_broken_pipe_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that broken pipe raises PrinterConnectionError."""
        connected_network._socket.sendall.side_effect = BrokenPipeError("Broken pipe")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, BrokenPipeError)

    def test_write_connection_reset_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that connection reset raises PrinterConnectionError."""
        connected_network._socket.sendall.side_effect = ConnectionResetError("Connection reset")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.write(b"test data")

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, ConnectionResetError)


class TestConnectionNetworkRead:
    """Test ConnectionNetwork read method error handling."""

    @pytest.fixture
    def connected_network(self) -> ConnectionNetwork:
        """Create a ConnectionNetwork with mocked socket."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            conn = ConnectionNetwork("192.168.1.100")
            return conn

    def test_read_timeout_raises_printer_error(self, connected_network: ConnectionNetwork) -> None:
        """Test that read timeout raises PrinterConnectionError."""
        connected_network._socket.recv.side_effect = socket.timeout("timed out")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.read()

        assert "timed out" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, socket.timeout)

    def test_read_broken_pipe_raises_printer_error(
        self, connected_network: ConnectionNetwork
    ) -> None:
        """Test that broken pipe raises PrinterConnectionError."""
        connected_network._socket.recv.side_effect = BrokenPipeError("Broken pipe")

        with pytest.raises(PrinterConnectionError) as exc_info:
            connected_network.read()

        assert "lost" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_error, BrokenPipeError)
