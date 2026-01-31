# ptouch

[![Tests](https://github.com/nbuchwitz/python3-ptouch/actions/workflows/pytest.yml/badge.svg)](https://github.com/nbuchwitz/python3-ptouch/actions/workflows/pytest.yml)
[![Linting](https://github.com/nbuchwitz/python3-ptouch/actions/workflows/lint.yml/badge.svg)](https://github.com/nbuchwitz/python3-ptouch/actions/workflows/lint.yml)

A Python library for Brother P-touch label printers.

## Features

- Support for Brother P-touch label printers (PT-E550W, PT-P750W, PT-P900W, PT-P950NW)
- Network (TCP/IP) and USB connections
- Text labels with customizable fonts and alignment
- Image label printing
- Multi-label printing with half-cut support (saves tape)
- High resolution mode support
- TIFF compression for efficient data transfer

## Installation

```bash
pip install ptouch
```

### Dependencies

- Python 3.11+
- Pillow
- packbits

For USB support:
- pyusb

## Supported Devices

### Printers

| Printer | Resolution | High-Res | Pins | Max Tape Width | Class |
|---------|------------|----------|------|----------------|-------|
| PT-E550W | 180 DPI | 360 DPI | 128 | 24mm | `PTE550W` |
| PT-P750W | 180 DPI | 360 DPI | 128 | 24mm | `PTP750W` |
| PT-P900W | 360 DPI | 720 DPI | 560 | 36mm | `PTP900` |
| PT-P950NW | 360 DPI | 720 DPI | 560 | 36mm | `PTP900` |

### Tapes

| Type | Widths | Class |
|------|--------|-------|
| Laminated (TZe) | 6mm, 9mm, 12mm, 18mm, 24mm, 36mm | `LaminatedTape*mm` |

## Adding Support for New Devices

### Adding a New Printer

To add support for a new P-touch printer, create a subclass of `LabelPrinter` in `ptouch/printers.py`:

```python
from ptouch.printer import LabelPrinter
from ptouch.config import TapeConfig
from ptouch.tape import LaminatedTape12mm, LaminatedTape24mm  # etc.

class PTP710BT(LabelPrinter):
    """Brother PT-P710BT label printer."""

    # Print head specifications (from Brother raster command reference)
    TOTAL_PINS = 128          # Total pins in print head
    BYTES_PER_LINE = 16       # TOTAL_PINS / 8
    RESOLUTION_DPI = 180      # Base resolution
    RESOLUTION_DPI_HIGH = 360 # High resolution (0 if not supported)

    # Capability flags - what the printer supports
    SUPPORTS_AUTO_CUT = True
    SUPPORTS_HALF_CUT = True
    SUPPORTS_PAGE_NUMBER_CUTS = True

    # Default values for each feature (used when not specified at print time)
    DEFAULT_USE_COMPRESSION = True
    DEFAULT_AUTO_CUT = True
    DEFAULT_HALF_CUT = True
    DEFAULT_HIGH_RESOLUTION = False
    DEFAULT_PAGE_NUMBER_CUTS = False

    # Pin configuration for each tape width
    # Values from Brother raster command reference PDF
    PIN_CONFIGS = {
        LaminatedTape12mm: TapeConfig(left_pins=29, print_pins=70, right_pins=29),
        LaminatedTape24mm: TapeConfig(left_pins=0, print_pins=128, right_pins=0),
        # Add more tape sizes as needed
    }
```

The pin configuration values (`left_pins`, `print_pins`, `right_pins`) can be found in the
Brother raster command reference documentation for your printer model.

### Adding a New Tape Type

To add a new tape type, create a subclass of `Tape` or `LaminatedTape` in `ptouch/tape.py`:

```python
from ptouch.tape import LaminatedTape

class LaminatedTape48mm(LaminatedTape):
    """48mm laminated tape."""
    width_mm = 48
```

Then add the corresponding `TapeConfig` entries to each printer class that supports the tape

## Usage

### Command Line

```bash
# Print text label via network
python -m ptouch "Hello World" --host 192.168.1.100 --printer P900 \
    --tape-width 36 --font /path/to/font.ttf

# Print multiple labels (half-cut between, full cut after last)
python -m ptouch "Label 1" "Label 2" "Label 3" --host 192.168.1.100 \
    --printer P900 --tape-width 12 --font /path/to/font.ttf

# Print multiple labels with full cuts between each
python -m ptouch "Label 1" "Label 2" --full-cut --host 192.168.1.100 \
    --printer P900 --tape-width 12 --font /path/to/font.ttf

# Print image label via USB
python -m ptouch --image logo.png --usb --printer E550W --tape-width 12

# Print with options
python -m ptouch "Test" --host 192.168.1.100 --printer P900 --tape-width 24 \
    --font /path/to/font.ttf --high-resolution --align left top --margin 5

# Print 5 copies of a label
python -m ptouch "Asset Tag" --copies 5 --host 192.168.1.100 \
    --printer P900 --tape-width 12 --font /path/to/font.ttf
```

### Python API

#### Text Labels

```python
from ptouch import (
    ConnectionNetwork,
    PTP900,
    TextLabel,
    LaminatedTape36mm,
    Align,
)

# Connect to printer
connection = ConnectionNetwork("192.168.1.100")
printer = PTP900(connection, high_resolution=True)

# Create and print text label
label = TextLabel(
    "Hello World",
    LaminatedTape36mm,
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    align=Align.CENTER,
)
printer.print(label)
```

#### Image Labels

```python
from PIL import Image
from ptouch import ConnectionNetwork, PTP900, Label, LaminatedTape36mm

connection = ConnectionNetwork("192.168.1.100")
printer = PTP900(connection)

image = Image.open("label.png")
label = Label(image, LaminatedTape36mm)
printer.print(label, margin_mm=3.0)
```

#### USB Connection

```python
from ptouch import ConnectionUSB, PTE550W, TextLabel, LaminatedTape12mm

connection = ConnectionUSB(PTE550W)
printer = PTE550W(connection)

label = TextLabel(
    "USB Label",
    LaminatedTape12mm,
    font_path="/path/to/font.ttf",
)
printer.print(label)
```

#### Multi-Label Printing

Print multiple labels in a single job with half-cuts between labels to save tape:

```python
from ptouch import ConnectionNetwork, PTP900, TextLabel, LaminatedTape12mm

connection = ConnectionNetwork("192.168.1.100")
printer = PTP900(connection)

labels = [
    TextLabel("Label 1", LaminatedTape12mm, font_path="/path/to/font.ttf"),
    TextLabel("Label 2", LaminatedTape12mm, font_path="/path/to/font.ttf"),
    TextLabel("Label 3", LaminatedTape12mm, font_path="/path/to/font.ttf"),
]

# Half-cuts between labels (default), full cut after last
printer.print_multi(labels)

# Or use full cuts between all labels
printer.print_multi(labels, half_cut=False)
```

### Alignment Options

Text alignment can be combined using the `|` operator:

```python
from ptouch import Align

# Horizontal: LEFT, HCENTER, RIGHT
# Vertical: TOP, VCENTER, BOTTOM
# Combined: CENTER (= HCENTER | VCENTER)

align = Align.LEFT | Align.TOP
align = Align.RIGHT | Align.BOTTOM
align = Align.CENTER  # centered both ways
```

## CLI Options

```
usage: python -m ptouch [-h] [--image FILE] (--host IP | --usb) --printer {E550W,P750W,P900,P900W,P950NW}
                        --tape-width {6,9,12,18,24,36} [--font PATH] [--font-size PX]
                        [--align H V] [--high-resolution] [--margin MM] [--no-compression]
                        [--full-cut] [text ...]

positional arguments:
  text                  Text to print. Multiple strings create multiple labels
                        with half-cut between (required unless --image is used)

options:
  --image, -i FILE      Image file to print instead of text
  --host, -H IP         Printer IP address for network connection
  --usb                 Use USB connection
  --printer, -p         Printer model
  --tape-width, -t      Tape width in mm
  --font, -f PATH       Path to TrueType font file (required for text labels)
  --font-size PX        Font size in pixels (default: 80% of print height)
  --align, -a H V       Horizontal and vertical alignment (default: center center)
  --high-resolution     Enable high resolution mode
  --margin, -m MM       Margin in mm (default: 2mm)
  --no-compression      Disable TIFF compression
  --full-cut            Use full cuts between labels instead of half-cuts
  --copies, -c N        Number of copies to print (default: 1)
```

## License

LGPL-2.1-or-later - see [LICENSE](LICENSE) for details.

## Author

Nicolai Buchwitz <nb@tipi-net.de>
