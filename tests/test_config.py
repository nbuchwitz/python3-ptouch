# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the TapeConfig class and USB constants."""

from ptouch.connection import USB_VENDOR_ID
from ptouch.printer import TapeConfig
from ptouch.printers import PTE550W, PTP750W, PTP900


class TestTapeConfig:
    """Test TapeConfig dataclass."""

    def test_tape_config_creation(self) -> None:
        """Test creating a TapeConfig instance."""
        config = TapeConfig(left_pins=10, print_pins=100, right_pins=18)
        assert config.left_pins == 10
        assert config.print_pins == 100
        assert config.right_pins == 18

    def test_tape_config_is_dataclass(self) -> None:
        """Test that TapeConfig is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(TapeConfig)

    def test_tape_config_equality(self) -> None:
        """Test that TapeConfig instances are compared by value."""
        config1 = TapeConfig(left_pins=10, print_pins=100, right_pins=18)
        config2 = TapeConfig(left_pins=10, print_pins=100, right_pins=18)
        config3 = TapeConfig(left_pins=20, print_pins=100, right_pins=8)
        assert config1 == config2
        assert config1 != config3

    def test_tape_config_repr(self) -> None:
        """Test that TapeConfig has a useful repr."""
        config = TapeConfig(left_pins=10, print_pins=100, right_pins=18)
        repr_str = repr(config)
        assert "TapeConfig" in repr_str
        assert "10" in repr_str
        assert "100" in repr_str
        assert "18" in repr_str

    def test_tape_config_importable_from_package(self) -> None:
        """Test that TapeConfig can be imported from ptouch."""
        from ptouch import TapeConfig as ImportedTapeConfig

        assert ImportedTapeConfig is TapeConfig


class TestUSBConstants:
    """Test USB constant values."""

    def test_usb_vendor_id(self) -> None:
        """Test Brother USB vendor ID."""
        # Brother Industries vendor ID
        assert USB_VENDOR_ID == 0x04F9

    def test_usb_product_id_e550w(self) -> None:
        """Test PT-E550W product ID."""
        assert PTE550W.USB_PRODUCT_ID == 0x2060

    def test_usb_product_id_p750w(self) -> None:
        """Test PT-P750W product ID."""
        assert PTP750W.USB_PRODUCT_ID == 0x2065

    def test_usb_product_id_p900w(self) -> None:
        """Test PT-P900W product ID."""
        assert PTP900.USB_PRODUCT_ID == 0x2085

    def test_vendor_and_product_ids_are_different(self) -> None:
        """Test that vendor and product IDs are all different."""
        ids = [
            USB_VENDOR_ID,
            PTE550W.USB_PRODUCT_ID,
            PTP750W.USB_PRODUCT_ID,
            PTP900.USB_PRODUCT_ID,
        ]
        assert len(ids) == len(set(ids))
