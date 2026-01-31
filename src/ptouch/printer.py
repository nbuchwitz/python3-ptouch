# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Base class for Brother P-touch label printers."""

import logging
import struct
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from math import ceil

import packbits
from PIL import Image

from .connection import Connection
from .label import Label
from .tape import Tape


@dataclass
class TapeConfig:
    """Pin configuration for a specific printer/tape combination.

    Attributes
    ----------
    left_pins : int
        Number of unused pins on the left margin.
    print_pins : int
        Number of pins in the printable area.
    right_pins : int
        Number of unused pins on the right margin.
    """

    left_pins: int
    print_pins: int
    right_pins: int


class MediaType(Enum):
    """Media type identifiers for Brother P-touch printers."""

    NO_MEDIA = 0x00
    LAMINATED_TAPE = 0x01
    NONLAMINATED_TAPE = 0x03
    HEATSHRINK_TUBE_21 = 0x11
    INCOMPATIBLE_TAPE = 0xFF


logger = logging.getLogger(__name__)


class LabelPrinter(ABC):
    """Abstract base class for Brother P-touch label printers.

    Subclasses must define the following class attributes:

    Attributes
    ----------
    TOTAL_PINS : int
        Total number of print head pins.
    BYTES_PER_LINE : int
        Number of bytes per raster line.
    RESOLUTION_DPI : int
        Base (vertical) resolution in DPI.
    RESOLUTION_DPI_HIGH : int
        High (horizontal) resolution in DPI when enabled.
    DEFAULT_USE_COMPRESSION : bool
        Whether to use TIFF compression by default.
    PIN_CONFIGS : dict[type[Tape], TapeConfig]
        Dict mapping tape type to TapeConfig.
    """

    # Subclasses must define these
    TOTAL_PINS: int
    BYTES_PER_LINE: int
    RESOLUTION_DPI: int
    RESOLUTION_DPI_HIGH: int = 0  # 0 means no high resolution support
    DEFAULT_USE_COMPRESSION: bool
    PIN_CONFIGS: dict[type[Tape], TapeConfig]

    # Capability flags - what the printer supports
    SUPPORTS_AUTO_CUT: bool = True
    SUPPORTS_HALF_CUT: bool = True
    SUPPORTS_PAGE_NUMBER_CUTS: bool = True

    # Default values for each feature (used when not specified)
    DEFAULT_AUTO_CUT: bool = True
    DEFAULT_HALF_CUT: bool = True
    DEFAULT_HIGH_RESOLUTION: bool = False
    DEFAULT_PAGE_NUMBER_CUTS: bool = False

    @property
    def supports_high_resolution(self) -> bool:
        """Whether the printer supports high resolution mode."""
        return self.RESOLUTION_DPI_HIGH > 0

    # Margin constraints in mm. See manual section "2.3.3 Feed amount".
    MIN_MARGIN_MM: float = 2.0
    MAX_MARGIN_MM: float = 127.0
    DEFAULT_MARGIN_MM: float = 2.0

    def _mm_to_dots(self, mm: float) -> int:
        """Convert millimeters to dots at base resolution."""
        return round(mm * self.RESOLUTION_DPI / 25.4)

    def __init__(
        self,
        connection: Connection,
        use_compression: bool | None = None,
        high_resolution: bool | None = None,
    ) -> None:
        """Initialize the label printer.

        Parameters
        ----------
        connection : Connection
            Connection to the printer (USB or network).
        use_compression : bool or None, optional
            Whether to use TIFF compression. Defaults to class setting.
        high_resolution : bool or None, optional
            Whether to use high resolution mode. Defaults to class setting.
        """
        self.connection = connection
        connection.connect(self)
        self.use_compression = (
            self.DEFAULT_USE_COMPRESSION if use_compression is None else use_compression
        )
        self.high_resolution = (
            self.DEFAULT_HIGH_RESOLUTION if high_resolution is None else high_resolution
        )

    def get_tape_config(self, tape: Tape) -> TapeConfig:
        """Get the tape configuration for a given tape.

        Parameters
        ----------
        tape : Tape
            The tape to get configuration for.

        Returns
        -------
        TapeConfig
            Pin configuration for the tape.

        Raises
        ------
        ValueError
            If the tape type is not supported by this printer.
        """
        tape_type = type(tape)
        if tape_type not in self.PIN_CONFIGS:
            supported = ", ".join(
                t.__name__ for t in sorted(self.PIN_CONFIGS.keys(), key=lambda t: t.width_mm)
            )
            raise ValueError(
                f"{tape_type.__name__} is not supported by {self.__class__.__name__}. "
                f"Supported tapes: {supported}"
            )
        return self.PIN_CONFIGS[tape_type]

    def _cmd_invalidate(self, length: int = 200) -> bytes:
        """Send invalidate command (null bytes) to clear printer buffer."""
        return b"\x00" * length

    def _cmd_initialize(self) -> bytes:
        """Send initialize command (ESC @)."""
        return b"\x1b\x40"

    def _cmd_invalidate_and_initialize(self) -> bytes:
        """Send invalidate followed by initialize commands."""
        return self._cmd_invalidate() + self._cmd_initialize()

    def _cmd_raster_mode(self) -> bytes:
        """Set printer to raster graphics mode (ESC i a)."""
        return struct.pack("BBBB", 0x1B, 0x69, 0x61, 0x01)

    def _cmd_print_information(
        self, length: int, media_type: MediaType, tape_width_mm: int
    ) -> bytes:
        """Set print information command (ESC i z).

        Parameters
        ----------
        length : int
            Number of raster lines to print.
        media_type : MediaType
            Type of media being used.
        tape_width_mm : int
            Tape width in millimeters.

        Returns
        -------
        bytes
            Command bytes for print information.
        """
        PI_WIDTH = 0x04  # Tape width valid
        PI_RECOVER = 0x80  # Recover mode (priority to print quality)
        n1 = PI_RECOVER | PI_WIDTH

        return struct.pack(
            "<7BL2B",
            0x1B,
            0x69,
            0x7A,
            n1,
            media_type.value,
            tape_width_mm,
            0x00,
            ceil(length),
            0x00,
            0x00,
        )

    def _cmd_mode_settings(self, auto_cut: bool = True, mirror_print: bool = False) -> bytes:
        """Set mode settings (ESC i M).

        Parameters
        ----------
        auto_cut : bool, default True
            Enable automatic cutting after print.
        mirror_print : bool, default False
            Enable mirror printing.

        Returns
        -------
        bytes
            Command bytes for mode settings.
        """
        mode = 0
        if auto_cut:
            mode |= 1 << 6
        if mirror_print:
            mode |= 1 << 7
        return struct.pack("4B", 0x1B, 0x69, 0x4D, mode)

    def _cmd_advanced_mode_settings(
        self,
        half_cut: bool = False,
        chain_printing: bool = False,
        high_resolution: bool = False,
    ) -> bytes:
        """Advanced mode settings (ESC i K).

        Parameters
        ----------
        half_cut : bool, default False
            Enable half-cut (cuts tape but not backing).
        chain_printing : bool, default False
            Enable chain printing (no cut between labels).
        high_resolution : bool, default False
            Enable high resolution mode.

        Returns
        -------
        bytes
            Command bytes for advanced mode settings.

        Notes
        -----
        Bit 0: Draft printing (1=draft, 0=normal)
        Bit 2: Half cut (1=on, 0=off)
        Bit 3: No chain printing (1=no chain, 0=chain)
        Bit 6: High resolution (1=yes, 0=no)
        """
        mode = 0
        if half_cut:
            mode |= 1 << 2
        if not chain_printing:
            mode |= 1 << 3
        if high_resolution:
            mode |= 1 << 6
        return struct.pack("4B", 0x1B, 0x69, 0x4B, mode)

    def _cmd_margin(self, margin: int = 14) -> bytes:
        """Set margin in dots (ESC i d).

        Parameters
        ----------
        margin : int, default 14
            Margin size in dots.

        Returns
        -------
        bytes
            Command bytes for margin setting.
        """
        return struct.pack("5B", 0x1B, 0x69, 0x64, margin & 0xFF, (margin >> 8) & 0xFF)

    def _cmd_set_compression(self, tiff_compression: bool = False) -> bytes:
        """Set compression mode (M).

        Parameters
        ----------
        tiff_compression : bool, default False
            Enable TIFF/PackBits compression.

        Returns
        -------
        bytes
            Command bytes for compression setting.
        """
        compression = 0x02 if tiff_compression else 0x00
        return struct.pack("2B", 0x4D, compression)

    def _cmd_page_number_cuts(self, pages: int = 1) -> bytes:
        """Set page number for auto-cut (ESC i A).

        Parameters
        ----------
        pages : int, default 1
            Number of pages to print before cutting (1 = cut each label).

        Returns
        -------
        bytes
            Command bytes for page number setting.
        """
        return struct.pack("4B", 0x1B, 0x69, 0x41, pages)

    def _prepare_image(self, image: Image.Image, tape_config: TapeConfig) -> Image.Image:
        """Prepare image for printing: resize, center, and convert to 1-bit.

        Parameters
        ----------
        image : PIL.Image.Image
            PIL Image to prepare.
        tape_config : TapeConfig
            Pin configuration for the tape.

        Returns
        -------
        PIL.Image.Image
            1-bit PIL Image ready for rasterization.
        """
        config = tape_config

        # Create container image with proper height
        container_image = Image.new("RGB", (image.width, config.print_pins), (255, 255, 255))
        # Compensate for asymmetric physical margins (left_pins vs right_pins)
        # to center content on the physical tape, not just within print area
        pin_offset = (config.right_pins - config.left_pins) // 2
        y = (config.print_pins - image.height) // 2 + pin_offset
        container_image.paste(image, (0, y))

        # Convert to 1-bit with threshold
        img_gray = container_image.convert("L")
        threshold_table = [0] * 128 + [255] * 128
        return img_gray.point(threshold_table, mode="1")

    def _generate_raster(self, img_1bit: Image.Image, tape_config: TapeConfig) -> bytes:
        """Generate raster data from 1-bit image.

        Parameters
        ----------
        img_1bit : PIL.Image.Image
            1-bit PIL Image to convert to raster data.
        tape_config : TapeConfig
            Pin configuration for the tape.

        Returns
        -------
        bytes
            Raster data bytes for the printer.
        """
        config = tape_config

        # Use pixel access object for faster pixel reading
        pixels = img_1bit.load()
        assert pixels is not None, "Failed to load image pixels"

        # Pre-allocate column bits array (reused for each column)
        column_bits = [0] * self.TOTAL_PINS

        # Build raster column by column
        raster = bytearray(img_1bit.width * self.BYTES_PER_LINE)
        raster_idx = 0

        for column in range(img_1bit.width):
            # Left margin pins are already 0 from initialization
            # Read print area pixels
            for row in range(config.print_pins):
                # In 1-bit images: 0 = black (print), 255 = white (no print)
                column_bits[config.left_pins + row] = 1 if pixels[column, row] == 0 else 0

            # Right margin pins are already 0 from initialization

            # Pack bits into bytes
            for i in range(0, self.TOTAL_PINS, 8):
                byte = 0
                for j in range(8):
                    if column_bits[i + j]:
                        byte |= 1 << (7 - j)
                raster[raster_idx] = byte
                raster_idx += 1

            # Reset print area for next column (margins stay 0)
            for row in range(config.print_pins):
                column_bits[config.left_pins + row] = 0

        return bytes(raster)

    def _additional_control_commands(self) -> bytes:
        """Return printer-specific control commands.

        Default implementation adds page number cuts if USE_PAGE_NUMBER_CUTS is True.
        Override in subclasses to add device-specific commands.
        """
        if self.DEFAULT_PAGE_NUMBER_CUTS:
            return self._cmd_page_number_cuts()
        return b""

    def _build_control_sequence(
        self, num_lines: int, margin: int, tape_width_mm: int, high_resolution: bool
    ) -> bytes:
        """Build control sequence using class attributes and optional hooks.

        Parameters
        ----------
        num_lines : int
            Number of raster lines in the image.
        margin : int
            Margin in dots (normal resolution).
        tape_width_mm : int
            Tape width in millimeters.
        high_resolution : bool
            Whether to use high resolution mode.

        Returns
        -------
        bytes
            Complete control sequence bytes to send before raster data.
        """
        # High resolution mode doubles lines and margin
        if high_resolution:
            num_lines *= 2
            margin *= 2

        control_seq = self._cmd_invalidate_and_initialize()
        control_seq += self._cmd_raster_mode()
        control_seq += (
            self._additional_control_commands()
        )  # Printer-specific commands (e.g., ESC i U)
        # Use NO_MEDIA to let printer auto-detect tape type
        media_type = MediaType.NO_MEDIA
        control_seq += self._cmd_print_information(num_lines, media_type, tape_width_mm)
        control_seq += self._cmd_mode_settings(auto_cut=self.DEFAULT_AUTO_CUT)
        control_seq += self._cmd_advanced_mode_settings(
            half_cut=self.DEFAULT_HALF_CUT,
            chain_printing=False,
            high_resolution=high_resolution,
        )
        control_seq += self._cmd_margin(margin)
        control_seq += self._cmd_set_compression(tiff_compression=self.use_compression)
        return control_seq

    def _build_page_control_sequence(
        self,
        num_lines: int,
        margin: int,
        tape_width_mm: int,
        high_resolution: bool,
        is_first_page: bool,
        auto_cut: bool = True,
        half_cut: bool = False,
        chain_printing: bool = False,
    ) -> bytes:
        """Build control sequence for a single page in a multi-page job.

        Parameters
        ----------
        num_lines : int
            Number of raster lines in the image.
        margin : int
            Margin in dots (normal resolution).
        tape_width_mm : int
            Tape width in millimeters.
        high_resolution : bool
            Whether to use high resolution mode.
        is_first_page : bool
            Whether this is the first page (needs invalidate/initialize).
        auto_cut : bool, default True
            Enable automatic cutting.
        half_cut : bool, default False
            Enable half-cut mode.
        chain_printing : bool, default False
            Enable chain printing (no cut after label).

        Returns
        -------
        bytes
            Control sequence bytes for this page.
        """
        # High resolution mode doubles lines and margin
        if high_resolution:
            num_lines *= 2
            margin *= 2

        control_seq = b""

        # Only first page gets invalidate and initialize
        if is_first_page:
            control_seq += self._cmd_invalidate_and_initialize()

        control_seq += self._cmd_raster_mode()
        control_seq += self._additional_control_commands()
        # Use NO_MEDIA to let printer auto-detect tape type
        media_type = MediaType.NO_MEDIA
        control_seq += self._cmd_print_information(num_lines, media_type, tape_width_mm)
        control_seq += self._cmd_mode_settings(auto_cut=auto_cut)
        if auto_cut and self.SUPPORTS_PAGE_NUMBER_CUTS:
            control_seq += self._cmd_page_number_cuts(pages=1)
        control_seq += self._cmd_advanced_mode_settings(
            half_cut=half_cut,
            chain_printing=chain_printing,
            high_resolution=high_resolution,
        )
        control_seq += self._cmd_margin(margin)
        control_seq += self._cmd_set_compression(tiff_compression=self.use_compression)
        return control_seq

    def _build_raster_data(self, raster: bytes, num_lines: int, high_resolution: bool) -> bytes:
        """Build raster data bytes from raw raster.

        Parameters
        ----------
        raster : bytes
            Raw raster data from _generate_raster.
        num_lines : int
            Number of raster lines.
        high_resolution : bool
            Whether to use high resolution mode.

        Returns
        -------
        bytes
            Formatted raster data for the printer.
        """
        repeat_count = 2 if high_resolution else 1

        raster_data = b""
        for i in range(num_lines):
            line_data = raster[i * self.BYTES_PER_LINE : (i + 1) * self.BYTES_PER_LINE]

            for _ in range(repeat_count):
                if self.use_compression:
                    # TIFF/packbits compression
                    if line_data == b"\x00" * self.BYTES_PER_LINE:
                        raster_data += b"\x5a"  # Z - Zero raster graphics
                    else:
                        compressed_line = packbits.encode(line_data)
                        raster_data += b"\x47"  # G - Raster graphics transfer
                        raster_data += struct.pack("<H", len(compressed_line))
                        raster_data += compressed_line
                else:
                    # No compression - send all lines including empty ones
                    raster_data += b"\x47"  # G - Raster graphics transfer
                    raster_data += struct.pack("<H", self.BYTES_PER_LINE)
                    raster_data += line_data

        return raster_data

    def print(
        self,
        label: Label,
        margin_mm: float | None = None,
        high_resolution: bool | None = None,
    ) -> None:
        """Print a label using column-by-column raster format.

        Parameters
        ----------
        label : Label
            Label to print (contains image and tape information).
        margin_mm : float or None, optional
            Margin in millimeters. Valid range: MIN_MARGIN_MM to MAX_MARGIN_MM.
            If None, uses DEFAULT_MARGIN_MM.
        high_resolution : bool or None, optional
            Whether to use high resolution mode. If None, uses printer's setting.

        Raises
        ------
        ValueError
            If the label's tape type is not supported by this printer.
        """
        # Resolve high_resolution setting
        high_res = self.high_resolution if high_resolution is None else high_resolution

        tape_config = self.get_tape_config(label.tape)
        label.prepare(tape_config.print_pins, self.RESOLUTION_DPI)
        image = label.image

        img_1bit = self._prepare_image(image, tape_config)
        raster = self._generate_raster(img_1bit, tape_config)
        num_lines = image.width

        # Resolve margin and validate bounds
        margin_mm = margin_mm if margin_mm is not None else self.DEFAULT_MARGIN_MM
        if not self.MIN_MARGIN_MM <= margin_mm <= self.MAX_MARGIN_MM:
            raise ValueError(
                f"Margin must be between {self.MIN_MARGIN_MM} and {self.MAX_MARGIN_MM} mm, "
                f"got {margin_mm}"
            )
        margin_dots = self._mm_to_dots(margin_mm)

        logger.info(f"Image: {image.size}")
        logger.info(
            f"{self.__class__.__name__}: {len(raster)} bytes, {num_lines} columns, "
            f"{self.BYTES_PER_LINE} bytes/column"
        )
        logger.info(f"Tape: {label.tape.width_mm}mm")
        logger.info(f"Margin: {margin_mm}mm ({margin_dots} dots)")
        logger.info(f"Compression: {'ON (TIFF)' if self.use_compression else 'OFF'}")
        if high_res:
            logger.info(f"Resolution: High ({self.RESOLUTION_DPI}x{self.RESOLUTION_DPI_HIGH} dpi)")
        else:
            logger.info(f"Resolution: Standard ({self.RESOLUTION_DPI}x{self.RESOLUTION_DPI} dpi)")

        control_seq = self._build_control_sequence(
            num_lines, margin_dots, label.tape.width_mm, high_res
        )

        raster_data = self._build_raster_data(raster, num_lines, high_res)

        # Send all data to printer in one write to avoid TCP fragmentation issues
        all_data = control_seq + raster_data + b"\x1a" + self._cmd_invalidate_and_initialize()
        self.connection.write(all_data)

        logger.info("Sent all data to printer.")

    def print_multi(
        self,
        labels: list[Label],
        margin_mm: float | None = None,
        high_resolution: bool | None = None,
        half_cut: bool = True,
    ) -> None:
        """Print multiple labels with cuts between and after last.

        This method prints multiple labels in sequence, with configurable
        cutting behavior between labels.

        Parameters
        ----------
        labels : list[Label]
            List of labels to print. All labels must use the same tape type.
        margin_mm : float or None, optional
            Margin in millimeters. Valid range: MIN_MARGIN_MM to MAX_MARGIN_MM.
            If None, uses DEFAULT_MARGIN_MM.
        high_resolution : bool or None, optional
            Whether to use high resolution mode. If None, uses printer's setting.
        half_cut : bool, default True
            If True, use half-cuts between labels (saves tape).
            If False, use full cuts between all labels.

        Raises
        ------
        ValueError
            If labels list is empty, tape types don't match, or tape is unsupported.
        """
        if not labels:
            raise ValueError("At least one label is required")

        # Verify all labels use the same tape type
        tape_type = type(labels[0].tape)
        for i, label in enumerate(labels[1:], start=2):
            if not isinstance(label.tape, tape_type):
                raise ValueError(
                    f"All labels must use the same tape type. "
                    f"Label 1 uses {tape_type.__name__}, label {i} uses {type(label.tape).__name__}"
                )

        # Resolve settings
        high_res = self.high_resolution if high_resolution is None else high_resolution
        margin_mm = margin_mm if margin_mm is not None else self.DEFAULT_MARGIN_MM
        if not self.MIN_MARGIN_MM <= margin_mm <= self.MAX_MARGIN_MM:
            raise ValueError(
                f"Margin must be between {self.MIN_MARGIN_MM} and {self.MAX_MARGIN_MM} mm, "
                f"got {margin_mm}"
            )
        margin_dots = self._mm_to_dots(margin_mm)

        tape_config = self.get_tape_config(labels[0].tape)
        tape_width_mm = labels[0].tape.width_mm

        cut_type = "half-cut" if half_cut else "full-cut"
        logger.info(f"Printing {len(labels)} labels with {cut_type} between")
        logger.info(f"Tape: {tape_width_mm}mm")
        logger.info(f"Margin: {margin_mm}mm ({margin_dots} dots)")
        logger.info(f"Compression: {'ON (TIFF)' if self.use_compression else 'OFF'}")
        if high_res:
            logger.info(f"Resolution: High ({self.RESOLUTION_DPI}x{self.RESOLUTION_DPI_HIGH} dpi)")
        else:
            logger.info(f"Resolution: Standard ({self.RESOLUTION_DPI}x{self.RESOLUTION_DPI} dpi)")

        all_data = b""

        for idx, label in enumerate(labels):
            is_first = idx == 0
            is_last = idx == len(labels) - 1

            # Prepare label
            label.prepare(tape_config.print_pins, self.RESOLUTION_DPI)
            image = label.image
            img_1bit = self._prepare_image(image, tape_config)
            raster = self._generate_raster(img_1bit, tape_config)
            num_lines = image.width

            logger.info(f"Label {idx + 1}/{len(labels)}: {image.size}, {num_lines} columns")

            # Build control sequence for this page
            # Half-cut mode: auto_cut=OFF, half_cut=ON → half-cuts between, full cut after last
            # Full-cut mode: auto_cut=ON, half_cut=OFF → full cuts between all labels
            control_seq = self._build_page_control_sequence(
                num_lines=num_lines,
                margin=margin_dots,
                tape_width_mm=tape_width_mm,
                high_resolution=high_res,
                is_first_page=is_first,  # Only first label gets invalidate/init
                auto_cut=not half_cut,  # ON for full-cut mode, OFF for half-cut mode
                half_cut=half_cut,  # ON for half-cuts between labels
                chain_printing=False,  # OFF (bit 3 set) - each page independent
            )

            raster_data = self._build_raster_data(raster, num_lines, high_res)

            all_data += control_seq + raster_data

            # FF (0x0C) for non-last pages, Control-Z (0x1A) for last page
            if is_last:
                all_data += b"\x1a"
            else:
                all_data += b"\x0c"

        # End with invalidate and initialize (same as single print)
        all_data += self._cmd_invalidate_and_initialize()

        # Send all data to printer in one write
        self.connection.write(all_data)

        logger.info(f"Sent all data for {len(labels)} labels to printer.")
