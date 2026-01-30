# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.printer and ptouch.printers modules."""

import pytest
from PIL import Image

from ptouch.config import TapeConfig
from ptouch.label import Label
from ptouch.printer import LabelPrinter, MediaType
from ptouch.printers import PTE550W, PTP750W, PTP900
from ptouch.tape import (
    HeatShrinkTape,
    LaminatedTape6mm,
    LaminatedTape12mm,
    LaminatedTape24mm,
    LaminatedTape36mm,
)

from .conftest import MockConnection


class TestMediaType:
    """Test MediaType enum."""

    def test_media_type_values(self) -> None:
        """Test that MediaType enum has expected values."""
        assert MediaType.NO_MEDIA.value == 0x00
        assert MediaType.LAMINATED_TAPE.value == 0x01
        assert MediaType.NONLAMINATED_TAPE.value == 0x03
        assert MediaType.HEATSHRINK_TUBE_21.value == 0x11
        assert MediaType.INCOMPATIBLE_TAPE.value == 0xFF


class TestPTE550W:
    """Test PTE550W printer class."""

    def test_class_attributes(self) -> None:
        """Test that class attributes are correctly defined."""
        assert PTE550W.TOTAL_PINS == 128
        assert PTE550W.BYTES_PER_LINE == 16
        assert PTE550W.RESOLUTION_DPI == 180
        assert PTE550W.RESOLUTION_DPI_HIGH == 360
        assert PTE550W.DEFAULT_USE_COMPRESSION is True

    def test_initialization(self, mock_connection: MockConnection) -> None:
        """Test printer initialization."""
        printer = PTE550W(mock_connection)
        assert printer.connection is mock_connection
        assert printer.use_compression is True  # Default
        assert printer.high_resolution is False  # Default

    def test_initialization_with_custom_settings(self, mock_connection: MockConnection) -> None:
        """Test printer initialization with custom settings."""
        printer = PTE550W(mock_connection, use_compression=False, high_resolution=True)
        assert printer.use_compression is False
        assert printer.high_resolution is True

    def test_supports_high_resolution(self, mock_connection: MockConnection) -> None:
        """Test that E550W supports high resolution."""
        printer = PTE550W(mock_connection)
        assert printer.supports_high_resolution is True

    def test_pin_configs(self) -> None:
        """Test that PIN_CONFIGS contains expected tape types."""
        assert LaminatedTape6mm in PTE550W.PIN_CONFIGS
        assert LaminatedTape12mm in PTE550W.PIN_CONFIGS
        assert LaminatedTape24mm in PTE550W.PIN_CONFIGS
        # E550W doesn't support 36mm
        assert LaminatedTape36mm not in PTE550W.PIN_CONFIGS

    def test_get_tape_config(self, mock_connection: MockConnection) -> None:
        """Test getting tape configuration."""
        printer = PTE550W(mock_connection)
        tape = LaminatedTape12mm()
        config = printer.get_tape_config(tape)
        assert isinstance(config, TapeConfig)
        assert config.left_pins == 29
        assert config.print_pins == 70
        assert config.right_pins == 29
        # Total should equal TOTAL_PINS
        assert config.left_pins + config.print_pins + config.right_pins == 128

    def test_get_tape_config_unsupported_tape(self, mock_connection: MockConnection) -> None:
        """Test that unsupported tape raises ValueError."""
        printer = PTE550W(mock_connection)
        tape = LaminatedTape36mm()
        with pytest.raises(ValueError, match="not supported"):
            printer.get_tape_config(tape)


class TestPTP750W:
    """Test PTP750W printer class."""

    def test_inherits_from_e550w(self) -> None:
        """Test that P750W inherits from E550W."""
        assert issubclass(PTP750W, PTE550W)

    def test_same_attributes_as_e550w(self) -> None:
        """Test that P750W has same attributes as E550W."""
        assert PTP750W.TOTAL_PINS == PTE550W.TOTAL_PINS
        assert PTP750W.PIN_CONFIGS == PTE550W.PIN_CONFIGS


class TestPTP900:
    """Test PTP900 printer class."""

    def test_class_attributes(self) -> None:
        """Test that class attributes are correctly defined."""
        assert PTP900.TOTAL_PINS == 560
        assert PTP900.BYTES_PER_LINE == 70
        assert PTP900.RESOLUTION_DPI == 360
        assert PTP900.RESOLUTION_DPI_HIGH == 720
        assert PTP900.DEFAULT_USE_COMPRESSION is False

    def test_supports_36mm_tape(self) -> None:
        """Test that P900 supports 36mm tape."""
        assert LaminatedTape36mm in PTP900.PIN_CONFIGS

    def test_get_tape_config_36mm(self, mock_connection: MockConnection) -> None:
        """Test getting 36mm tape configuration."""
        printer = PTP900(mock_connection)
        tape = LaminatedTape36mm()
        config = printer.get_tape_config(tape)
        assert config.left_pins == 45
        assert config.print_pins == 454
        assert config.right_pins == 61
        assert config.left_pins + config.print_pins + config.right_pins == 560


class TestLabelPrinterCommands:
    """Test LabelPrinter command generation methods."""

    @pytest.fixture
    def printer(self, mock_connection: MockConnection) -> PTE550W:
        """Create a test printer."""
        return PTE550W(mock_connection)

    def test_cmd_invalidate(self, printer: PTE550W) -> None:
        """Test invalidate command generates correct null bytes."""
        cmd = printer._cmd_invalidate(length=100)
        assert len(cmd) == 100
        assert cmd == b"\x00" * 100

    def test_cmd_initialize(self, printer: PTE550W) -> None:
        """Test initialize command (ESC @)."""
        cmd = printer._cmd_initialize()
        assert cmd == b"\x1b\x40"

    def test_cmd_raster_mode(self, printer: PTE550W) -> None:
        """Test raster mode command (ESC i a)."""
        cmd = printer._cmd_raster_mode()
        assert cmd == b"\x1b\x69\x61\x01"

    def test_cmd_mode_settings_auto_cut_on(self, printer: PTE550W) -> None:
        """Test mode settings with auto-cut enabled."""
        cmd = printer._cmd_mode_settings(auto_cut=True, mirror_print=False)
        assert cmd[:3] == b"\x1b\x69\x4d"
        assert cmd[3] & (1 << 6) != 0  # Auto-cut bit set

    def test_cmd_mode_settings_auto_cut_off(self, printer: PTE550W) -> None:
        """Test mode settings with auto-cut disabled."""
        cmd = printer._cmd_mode_settings(auto_cut=False, mirror_print=False)
        assert cmd[:3] == b"\x1b\x69\x4d"
        assert cmd[3] & (1 << 6) == 0  # Auto-cut bit not set

    def test_cmd_advanced_mode_settings_high_res(self, printer: PTE550W) -> None:
        """Test advanced mode settings with high resolution enabled."""
        cmd = printer._cmd_advanced_mode_settings(high_resolution=True)
        assert cmd[:3] == b"\x1b\x69\x4b"
        assert cmd[3] & (1 << 6) != 0  # High-res bit set

    def test_cmd_margin(self, printer: PTE550W) -> None:
        """Test margin command."""
        cmd = printer._cmd_margin(margin=14)
        assert cmd[:3] == b"\x1b\x69\x64"
        # Margin is little-endian 16-bit
        assert cmd[3:5] == b"\x0e\x00"

    def test_cmd_set_compression_on(self, printer: PTE550W) -> None:
        """Test compression command enabled."""
        cmd = printer._cmd_set_compression(tiff_compression=True)
        assert cmd == b"\x4d\x02"

    def test_cmd_set_compression_off(self, printer: PTE550W) -> None:
        """Test compression command disabled."""
        cmd = printer._cmd_set_compression(tiff_compression=False)
        assert cmd == b"\x4d\x00"


class TestLabelPrinterMmToDots:
    """Test mm to dots conversion."""

    def test_mm_to_dots_e550w(self, mock_connection: MockConnection) -> None:
        """Test mm to dots conversion for 180 DPI printer."""
        printer = PTE550W(mock_connection)  # 180 DPI
        # 25.4mm = 1 inch = 180 dots
        assert printer._mm_to_dots(25.4) == 180
        # 2mm margin
        dots = printer._mm_to_dots(2.0)
        assert dots == round(2.0 * 180 / 25.4)  # ~14

    def test_mm_to_dots_p900(self, mock_connection: MockConnection) -> None:
        """Test mm to dots conversion for 360 DPI printer."""
        printer = PTP900(mock_connection)  # 360 DPI
        # 25.4mm = 1 inch = 360 dots
        assert printer._mm_to_dots(25.4) == 360


class TestLabelPrinterPrint:
    """Test the complete print workflow."""

    def test_print_sends_data(
        self, mock_connection: MockConnection, sample_image_with_content: Image.Image
    ) -> None:
        """Test that print sends data to the connection."""
        printer = PTE550W(mock_connection, use_compression=True)
        label = Label(sample_image_with_content, LaminatedTape12mm)
        printer.print(label)
        # Should have sent data
        assert len(mock_connection.data) > 0
        # Should start with invalidate (null bytes)
        assert mock_connection.data[:50] == b"\x00" * 50

    def test_print_with_custom_margin(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test print with custom margin."""
        printer = PTE550W(mock_connection)
        label = Label(sample_image, LaminatedTape12mm)
        printer.print(label, margin_mm=5.0)
        assert len(mock_connection.data) > 0

    def test_print_invalid_margin_too_small(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test that margin below minimum raises ValueError."""
        printer = PTE550W(mock_connection)
        label = Label(sample_image, LaminatedTape12mm)
        with pytest.raises(ValueError, match="Margin must be between"):
            printer.print(label, margin_mm=0.5)

    def test_print_invalid_margin_too_large(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test that margin above maximum raises ValueError."""
        printer = PTE550W(mock_connection)
        label = Label(sample_image, LaminatedTape12mm)
        with pytest.raises(ValueError, match="Margin must be between"):
            printer.print(label, margin_mm=200.0)

    def test_print_unsupported_tape(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test that printing with unsupported tape raises ValueError."""
        printer = PTE550W(mock_connection)
        label = Label(sample_image, LaminatedTape36mm)  # E550W doesn't support 36mm
        with pytest.raises(ValueError, match="not supported"):
            printer.print(label)

    def test_print_with_high_resolution(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test printing in high resolution mode."""
        printer = PTE550W(mock_connection)
        label = Label(sample_image, LaminatedTape12mm)
        printer.print(label, high_resolution=True)
        assert len(mock_connection.data) > 0

    def test_print_ends_with_print_command(
        self, mock_connection: MockConnection, sample_image: Image.Image
    ) -> None:
        """Test that print data ends with print command (0x1a) and initialize."""
        printer = PTE550W(mock_connection, use_compression=True)
        label = Label(sample_image, LaminatedTape12mm)
        printer.print(label)
        # Should contain print command
        assert b"\x1a" in mock_connection.data


class TestImagePreparation:
    """Test image preparation methods."""

    def test_prepare_image_returns_1bit(self, mock_connection: MockConnection) -> None:
        """Test that _prepare_image returns a 1-bit image."""
        printer = PTE550W(mock_connection)
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        tape = LaminatedTape12mm()
        config = printer.get_tape_config(tape)
        img_1bit = printer._prepare_image(img, config)
        assert img_1bit.mode == "1"

    def test_prepare_image_matches_print_pins_height(self, mock_connection: MockConnection) -> None:
        """Test that prepared image height matches print_pins."""
        printer = PTE550W(mock_connection)
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        tape = LaminatedTape12mm()
        config = printer.get_tape_config(tape)
        img_1bit = printer._prepare_image(img, config)
        assert img_1bit.height == config.print_pins

    def test_generate_raster_correct_length(self, mock_connection: MockConnection) -> None:
        """Test that raster data has correct length."""
        printer = PTE550W(mock_connection)
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        tape = LaminatedTape12mm()
        config = printer.get_tape_config(tape)
        img_1bit = printer._prepare_image(img, config)
        raster = printer._generate_raster(img_1bit, config)
        # Each column should have BYTES_PER_LINE bytes
        expected_length = img_1bit.width * printer.BYTES_PER_LINE
        assert len(raster) == expected_length
