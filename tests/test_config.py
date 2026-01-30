# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.config module."""

from ptouch.config import (
    TapeConfig,
    USB_PRODUCT_ID_PT_E550W,
    USB_PRODUCT_ID_PT_P900W,
    USB_VENDOR_ID,
)


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


class TestUSBConstants:
    """Test USB constant values."""

    def test_usb_vendor_id(self) -> None:
        """Test Brother USB vendor ID."""
        # Brother Industries vendor ID
        assert USB_VENDOR_ID == 0x04F9

    def test_usb_product_id_e550w(self) -> None:
        """Test PT-E550W product ID."""
        assert USB_PRODUCT_ID_PT_E550W == 0x2060

    def test_usb_product_id_p900w(self) -> None:
        """Test PT-P900W product ID."""
        assert USB_PRODUCT_ID_PT_P900W == 0x2085

    def test_vendor_and_product_ids_are_different(self) -> None:
        """Test that vendor and product IDs are all different."""
        ids = [USB_VENDOR_ID, USB_PRODUCT_ID_PT_E550W, USB_PRODUCT_ID_PT_P900W]
        assert len(ids) == len(set(ids))
