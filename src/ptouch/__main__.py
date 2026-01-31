# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""CLI interface for Brother P-touch label printers."""

import argparse
import sys
from typing import Sequence

from PIL import Image, ImageFont

from . import (
    Align,
    ConnectionNetwork,
    ConnectionUSB,
    Label,
    LaminatedTape6mm,
    LaminatedTape9mm,
    LaminatedTape12mm,
    LaminatedTape18mm,
    LaminatedTape24mm,
    LaminatedTape36mm,
    PTE550W,
    PTP750W,
    PTP900,
    TextLabel,
)
from .printer import LabelPrinter

# Mapping of tape width (mm) to tape classes
TAPE_WIDTHS = {
    6: LaminatedTape6mm,
    9: LaminatedTape9mm,
    12: LaminatedTape12mm,
    18: LaminatedTape18mm,
    24: LaminatedTape24mm,
    36: LaminatedTape36mm,
}

# Mapping of printer names to printer classes
PRINTER_TYPES = {
    "E550W": PTE550W,
    "P750W": PTP750W,
    "P900": PTP900,
    "P900W": PTP900,
    "P950NW": PTP900,
}

# Mapping of alignment strings to Align flags
ALIGN_HORIZONTAL = {
    "left": Align.LEFT,
    "center": Align.HCENTER,
    "right": Align.RIGHT,
}

ALIGN_VERTICAL = {
    "top": Align.TOP,
    "center": Align.VCENTER,
    "bottom": Align.BOTTOM,
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="python -m ptouch",
        description="Print labels on Brother P-touch printers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Print text label via network (uses PIL default font)
  python -m ptouch "Hello World" --host 192.168.1.100 --printer P900 --tape-width 36

  # Print with custom font
  python -m ptouch "Hello World" --host 192.168.1.100 --printer P900 \\
      --tape-width 36 --font /path/to/font.ttf

  # Print multiple labels (half-cut between, full cut after last)
  python -m ptouch "Label 1" "Label 2" "Label 3" --host 192.168.1.100 \\
      --printer E550W --tape-width 12

  # Print image label via USB
  python -m ptouch --image logo.png --usb --printer E550W --tape-width 12

  # Print with fixed font size (disables auto-sizing)
  python -m ptouch "Test" --host 192.168.1.100 --printer P900 \\
      --tape-width 24 --font-size 48 --high-resolution

  # Print 5 copies of a label
  python -m ptouch "Asset Tag" --copies 5 --host 192.168.1.100 \\
      --printer P900 --tape-width 12

  # Print label with fixed width (50mm)
  python -m ptouch "Short" --width 50 --host 192.168.1.100 \\
      --printer P900 --tape-width 12
""",
    )

    # Content (text or image)
    parser.add_argument(
        "text",
        nargs="*",
        help="Text to print. Multiple strings create multiple labels with half-cut between.",
    )
    parser.add_argument(
        "--image",
        "-i",
        metavar="FILE",
        help="Image file to print instead of text",
    )

    # Connection
    conn_group = parser.add_mutually_exclusive_group(required=True)
    conn_group.add_argument(
        "--host",
        "-H",
        metavar="IP",
        help="Printer IP address for network connection",
    )
    conn_group.add_argument(
        "--usb",
        action="store_true",
        help="Use USB connection",
    )

    # Printer and tape
    parser.add_argument(
        "--printer",
        "-p",
        required=True,
        choices=list(set(PRINTER_TYPES.keys())),
        help="Printer model",
    )
    parser.add_argument(
        "--tape-width",
        "-t",
        type=int,
        required=True,
        choices=list(TAPE_WIDTHS.keys()),
        help="Tape width in mm",
    )

    # Font options
    parser.add_argument(
        "--font",
        "-f",
        metavar="PATH",
        help="Path to TrueType font file (uses PIL default font if not specified)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        metavar="PX",
        help="Font size in pixels (disables auto-sizing to 80%% of print height)",
    )

    # Alignment
    parser.add_argument(
        "--align",
        "-a",
        nargs=2,
        metavar=("H", "V"),
        default=["center", "center"],
        help="Alignment: left|center|right top|center|bottom (default: center center)",
    )

    # Print options
    parser.add_argument(
        "--high-resolution",
        action="store_true",
        help="Enable high resolution mode",
    )
    parser.add_argument(
        "--margin",
        "-m",
        type=float,
        metavar="MM",
        help="Margin in mm (default: 2mm)",
    )
    parser.add_argument(
        "--no-compression",
        action="store_true",
        help="Disable TIFF compression",
    )
    parser.add_argument(
        "--full-cut",
        action="store_true",
        help="Use full cuts between labels instead of half-cuts (default: half-cut)",
    )
    parser.add_argument(
        "--copies",
        "-c",
        type=int,
        default=1,
        metavar="N",
        help="Number of copies to print (default: 1)",
    )
    parser.add_argument(
        "--width",
        "-w",
        type=float,
        metavar="MM",
        help="Fixed label width in mm (default: auto-sized to content)",
    )

    return parser.parse_args()


def create_text_labels(
    texts: Sequence[str],
    tape_class: type,
    font: str | ImageFont.FreeTypeFont,
    align: Align,
    font_size: int | None = None,
    min_width_mm: float | None = None,
    auto_size: bool = True,
) -> list[TextLabel]:
    """Create TextLabel instances for multiple text strings.

    Parameters
    ----------
    texts : Sequence[str]
        List of text strings to create labels for.
    tape_class : type
        Tape class to use for all labels.
    font : str or ImageFont.FreeTypeFont
        Path to TrueType font file or ImageFont object.
    align : Align
        Text alignment flags.
    font_size : int or None
        Font size in pixels (only used when auto_size=False).
    min_width_mm : float or None
        Minimum label width in millimeters.
    auto_size : bool
        If True, auto-size font to 80% of print height.

    Returns
    -------
    list[TextLabel]
        List of TextLabel instances.
    """
    return [
        TextLabel(
            text,
            tape_class,
            font=font,
            font_size=font_size,
            align=align,
            min_width_mm=min_width_mm,
            auto_size=auto_size,
        )
        for text in texts
    ]


def main() -> int:
    """Run the command-line interface."""
    args = parse_args()

    # Validate arguments
    if args.image and args.text:
        print("Error: Cannot specify both text and --image", file=sys.stderr)
        return 1

    if not args.image and not args.text:
        print("Error: Must specify either text or --image", file=sys.stderr)
        return 1

    if args.copies < 1:
        print("Error: --copies must be at least 1", file=sys.stderr)
        return 1

    # Get printer and tape classes
    printer_class = PRINTER_TYPES[args.printer]
    tape_class = TAPE_WIDTHS[args.tape_width]

    # Create connection
    if args.host:
        connection = ConnectionNetwork(args.host)
    else:
        connection = ConnectionUSB(printer_class)

    # Create printer
    use_compression = not args.no_compression
    printer = printer_class(
        connection,
        use_compression=use_compression,
        high_resolution=args.high_resolution,
    )

    # Create label(s)
    if args.image:
        image = Image.open(args.image)
        labels = [Label(image, tape_class)]
    else:
        # Parse alignment
        h_align = ALIGN_HORIZONTAL.get(args.align[0].lower())
        v_align = ALIGN_VERTICAL.get(args.align[1].lower())

        if h_align is None:
            print(
                f"Error: Invalid horizontal alignment '{args.align[0]}'. Use: left, center, right",
                file=sys.stderr,
            )
            return 1
        if v_align is None:
            print(
                f"Error: Invalid vertical alignment '{args.align[1]}'. Use: top, center, bottom",
                file=sys.stderr,
            )
            return 1

        align = h_align | v_align

        # Determine font: use provided path or try default font
        font: str | ImageFont.FreeTypeFont
        if args.font:
            font = args.font
        else:
            try:
                default_font = ImageFont.load_default()
                # Check if it's a scalable font (has font_variant method)
                if not hasattr(default_font, "font_variant") or not isinstance(
                    default_font, ImageFont.FreeTypeFont
                ):
                    print(
                        "Error: PIL default font is not scalable. "
                        "Please upgrade Pillow to 10.1+ or provide --font",
                        file=sys.stderr,
                    )
                    return 1
                font = default_font
            except Exception as e:
                print(f"Error: Could not load default font: {e}", file=sys.stderr)
                print("Please provide --font with a path to a TrueType font", file=sys.stderr)
                return 1

        # Calculate image width: --width is total label length, subtract margins (both sides)
        margin_mm = args.margin if args.margin is not None else LabelPrinter.DEFAULT_MARGIN_MM
        min_width_mm = None
        if args.width is not None:
            min_width_mm = args.width - (2 * margin_mm)
            if min_width_mm <= 0:
                print(
                    f"Error: --width must be greater than 2x margin ({2 * margin_mm}mm)",
                    file=sys.stderr,
                )
                return 1

        # auto_size=True (default) unless font_size is explicitly set
        auto_size = args.font_size is None

        labels = create_text_labels(
            args.text,
            tape_class,
            font=font,
            align=align,
            font_size=args.font_size,
            min_width_mm=min_width_mm,
            auto_size=auto_size,
        )

    # Apply copies
    if args.copies > 1:
        labels = labels * args.copies

    # Print
    num_labels = len(labels)
    use_half_cut = not args.full_cut
    conn_type = "network" if args.host else "USB"
    print(f"Printing {num_labels} label(s) to {printer_class.__name__} via {conn_type}...")
    print(
        f"Tape: {args.tape_width}mm, High-res: {args.high_resolution}, "
        f"Compression: {use_compression}"
    )
    if num_labels > 1:
        cut_type = "half-cut" if use_half_cut else "full-cut"
        print(f"Using {cut_type} between labels, full cut after last label.")

    try:
        if num_labels == 1:
            printer.print(labels[0], margin_mm=args.margin, high_resolution=args.high_resolution)
        else:
            printer.print_multi(
                labels,
                margin_mm=args.margin,
                high_resolution=args.high_resolution,
                half_cut=use_half_cut,
            )
        print("Done.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
