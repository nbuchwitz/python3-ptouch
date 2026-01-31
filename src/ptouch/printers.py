# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Concrete printer implementations for Brother P-touch label printers."""

from .printer import LabelPrinter, TapeConfig
from .tape import (
    LaminatedTape6mm,
    LaminatedTape9mm,
    LaminatedTape12mm,
    LaminatedTape18mm,
    LaminatedTape24mm,
    LaminatedTape36mm,
)


class PTE550W(LabelPrinter):
    """Brother PT-E550W label printer (128 pins, 180 DPI).

    Note: E550W requires compression ON for cutting to work.
    High resolution mode (180x360 dpi) is supported via ESC i K bit 6.
    In high-res mode, each raster line must be sent twice and margin doubled.
    """

    USB_PRODUCT_ID = 0x2060
    TOTAL_PINS = 128
    BYTES_PER_LINE = 16
    RESOLUTION_DPI = 180
    RESOLUTION_DPI_HIGH = 360
    DEFAULT_USE_COMPRESSION = True  # Required for cutting to work

    # Pin configurations from official Brother PT-E550W specification document
    # Source: cv_pte550wp750wp710bt_eng_raster_102.pdf, page 20, section "2.3 Print Area"
    PIN_CONFIGS = {
        LaminatedTape6mm: TapeConfig(left_pins=48, print_pins=32, right_pins=48),
        LaminatedTape9mm: TapeConfig(left_pins=39, print_pins=50, right_pins=39),
        LaminatedTape12mm: TapeConfig(left_pins=29, print_pins=70, right_pins=29),
        LaminatedTape18mm: TapeConfig(left_pins=8, print_pins=112, right_pins=8),
        LaminatedTape24mm: TapeConfig(left_pins=0, print_pins=128, right_pins=0),
    }


class PTP750W(PTE550W):
    """Brother PT-P750W label printer (128 pins, 180 DPI).

    Inherits all settings from PTE550W.
    """

    USB_PRODUCT_ID = 0x2065


class PTP900(LabelPrinter):
    """Brother PT-P900W/P900Wc label printer (560 pins, 360 DPI).

    This class supports the following printers:
        - PT-P900W
        - PT-P900Wc
    """

    USB_PRODUCT_ID = 0x2085
    TOTAL_PINS = 560
    BYTES_PER_LINE = 70
    RESOLUTION_DPI = 360
    RESOLUTION_DPI_HIGH = 720
    DEFAULT_USE_COMPRESSION = False

    # Pin configurations from official Brother PT-P900 specification document
    # Source: cv_ptp900_eng_raster_102.pdf, pages 23-24, section 2.3.5 "Raster line"
    PIN_CONFIGS = {
        LaminatedTape6mm: TapeConfig(left_pins=240, print_pins=64, right_pins=256),
        LaminatedTape9mm: TapeConfig(left_pins=219, print_pins=106, right_pins=235),
        LaminatedTape12mm: TapeConfig(left_pins=197, print_pins=150, right_pins=213),
        LaminatedTape18mm: TapeConfig(left_pins=155, print_pins=234, right_pins=171),
        LaminatedTape24mm: TapeConfig(left_pins=112, print_pins=320, right_pins=128),
        LaminatedTape36mm: TapeConfig(left_pins=45, print_pins=454, right_pins=61),
    }
