# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Brother P-touch label printer driver.

This module provides a Python interface for Brother P-touch label printers,
supporting both USB and network connections. It handles raster image generation,
compression, and printer-specific command sequences.

Supported printers:
    - PT-E550W (128 pins, 180 DPI)
    - PT-P750W (128 pins, 180 DPI)
    - PT-P900W / P900Wc (560 pins, 360 DPI)

Example usage:
    >>> from ptouch import PTP900, ConnectionNetwork, LaminatedTape36mm, TextLabel
    >>> conn = ConnectionNetwork("192.168.1.100")
    >>> printer = PTP900(conn)
    >>> label = TextLabel("Hello, World!", LaminatedTape36mm)
    >>> printer.print(label)
"""

from .connection import Connection, ConnectionNetwork, ConnectionUSB, PrinterConnectionError
from .label import Align, Label, TextLabel
from .printer import LabelPrinter, MediaType, TapeConfig
from .printers import PTE550W, PTP750W, PTP900
from .tape import (
    HeatShrinkTape,
    LaminatedTape,
    LaminatedTape6mm,
    LaminatedTape9mm,
    LaminatedTape12mm,
    LaminatedTape18mm,
    LaminatedTape24mm,
    LaminatedTape36mm,
    Tape,
)

__version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",
    # Enums
    "MediaType",
    "Align",
    # Config
    "TapeConfig",
    # Connections
    "Connection",
    "ConnectionUSB",
    "ConnectionNetwork",
    "PrinterConnectionError",
    # Printers
    "LabelPrinter",
    "PTE550W",
    "PTP750W",
    "PTP900",
    # Tapes
    "Tape",
    "LaminatedTape",
    "LaminatedTape6mm",
    "LaminatedTape9mm",
    "LaminatedTape12mm",
    "LaminatedTape18mm",
    "LaminatedTape24mm",
    "LaminatedTape36mm",
    "HeatShrinkTape",
    # Labels
    "Label",
    "TextLabel",
]
