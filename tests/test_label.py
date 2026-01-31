# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.label module."""

import warnings

import pytest
from PIL import Image, ImageFont

from ptouch.label import Align, Label, TextLabel
from ptouch.tape import LaminatedTape12mm, LaminatedTape36mm


class TestAlign:
    """Test Align enum."""

    def test_align_flags_are_distinct(self) -> None:
        """Test that alignment flags have distinct values."""
        flags = [Align.LEFT, Align.HCENTER, Align.RIGHT, Align.TOP, Align.VCENTER, Align.BOTTOM]
        values = [f.value for f in flags]
        assert len(values) == len(set(values)), "Alignment flags should have unique values"

    def test_textlabel_align_access(self) -> None:
        """Test that Align is accessible via TextLabel.Align."""
        assert TextLabel.Align is Align
        assert TextLabel.Align.CENTER == Align.CENTER
        assert TextLabel.Align.LEFT == Align.LEFT

    def test_align_center_combines_horizontal_and_vertical(self) -> None:
        """Test that CENTER is HCENTER | VCENTER."""
        assert Align.CENTER == (Align.HCENTER | Align.VCENTER)

    def test_align_flags_can_be_combined(self) -> None:
        """Test that alignment flags can be combined with |."""
        combined = Align.LEFT | Align.TOP
        assert Align.LEFT in combined
        assert Align.TOP in combined
        assert Align.RIGHT not in combined
        assert Align.BOTTOM not in combined

    def test_align_horizontal_flags(self) -> None:
        """Test that horizontal flags are correctly identified."""
        left_top = Align.LEFT | Align.TOP
        center_bottom = Align.HCENTER | Align.BOTTOM
        right_center = Align.RIGHT | Align.VCENTER

        assert Align.LEFT in left_top
        assert Align.HCENTER in center_bottom
        assert Align.RIGHT in right_center

    def test_align_vertical_flags(self) -> None:
        """Test that vertical flags are correctly identified."""
        left_top = Align.LEFT | Align.TOP
        center_bottom = Align.HCENTER | Align.BOTTOM
        right_center = Align.RIGHT | Align.VCENTER

        assert Align.TOP in left_top
        assert Align.BOTTOM in center_bottom
        assert Align.VCENTER in right_center


class TestLabel:
    """Test Label class."""

    def test_label_with_tape_class(self, sample_image: Image.Image) -> None:
        """Test Label initialization with tape class."""
        label = Label(sample_image, LaminatedTape36mm)
        assert label.image is sample_image
        assert isinstance(label.tape, LaminatedTape36mm)
        assert label.tape.width_mm == 36

    def test_label_with_tape_instance(self, sample_image: Image.Image) -> None:
        """Test Label initialization with tape instance."""
        tape = LaminatedTape12mm()
        label = Label(sample_image, tape)
        assert label.image is sample_image
        assert label.tape is tape
        assert label.tape.width_mm == 12

    def test_label_prepare_is_noop(self, sample_image: Image.Image) -> None:
        """Test that Label.prepare() does nothing (base implementation)."""
        label = Label(sample_image, LaminatedTape36mm)
        # Should not raise
        label.prepare(100)
        # Image should be unchanged
        assert label.image is sample_image


class TestTextLabel:
    """Test TextLabel class."""

    @pytest.fixture
    def font_path(self) -> str:
        """Return path to a system font for testing."""
        # Common font paths on various systems
        import os

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        pytest.skip("No suitable font found for testing")

    def test_text_label_initialization_with_tape_class(self, font_path: str) -> None:
        """Test TextLabel initialization with tape class."""
        label = TextLabel("Hello", LaminatedTape36mm, font_path)
        assert label.text == "Hello"
        assert isinstance(label.tape, LaminatedTape36mm)
        assert label.font == font_path
        assert label.font_size is None
        assert label.align == TextLabel.Align.CENTER

    def test_text_label_initialization_with_tape_instance(self, font_path: str) -> None:
        """Test TextLabel initialization with tape instance."""
        tape = LaminatedTape12mm()
        label = TextLabel("World", tape, font_path)
        assert label.text == "World"
        assert label.tape is tape

    def test_text_label_initialization_with_custom_font_size(self, font_path: str) -> None:
        """Test TextLabel initialization with custom font size."""
        label = TextLabel("Test", LaminatedTape36mm, font_path, font_size=48)
        assert label.font_size == 48

    def test_text_label_initialization_with_custom_align(self, font_path: str) -> None:
        """Test TextLabel initialization with custom alignment."""
        align = TextLabel.Align.LEFT | TextLabel.Align.TOP
        label = TextLabel("Test", LaminatedTape36mm, font_path, align=align)
        assert label.align == align

    def test_text_label_image_raises_before_prepare(self, font_path: str) -> None:
        """Test that accessing image before prepare() raises RuntimeError."""
        label = TextLabel("Hello", LaminatedTape36mm, font_path)
        with pytest.raises(RuntimeError, match="not been rendered yet"):
            _ = label.image

    def test_text_label_prepare_renders_image(self, font_path: str) -> None:
        """Test that prepare() renders the text to an image."""
        label = TextLabel("Hello", LaminatedTape36mm, font_path)
        label.prepare(height=100)
        img = label.image
        assert isinstance(img, Image.Image)
        assert img.height == 100
        assert img.width > 0

    def test_text_label_prepare_uses_default_font_size(self, font_path: str) -> None:
        """Test that prepare() uses 80% of height as default font size."""
        label = TextLabel("Test", LaminatedTape36mm, font_path)
        label.prepare(height=100)
        # Font size should be 80 (80% of 100)
        # We can't directly check font size, but the image should be rendered
        assert label.image is not None

    def test_text_label_prepare_is_idempotent(self, font_path: str) -> None:
        """Test that calling prepare() multiple times doesn't re-render."""
        label = TextLabel("Hello", LaminatedTape36mm, font_path)
        label.prepare(height=100)
        img1 = label.image
        label.prepare(height=200)  # Different height, but should not re-render
        img2 = label.image
        assert img1 is img2

    def test_text_label_image_is_rgb(self, font_path: str) -> None:
        """Test that rendered image is RGB mode."""
        label = TextLabel("Hello", LaminatedTape36mm, font_path)
        label.prepare(height=100)
        assert label.image.mode == "RGB"

    def test_text_label_different_alignments(self, font_path: str) -> None:
        """Test that different alignments produce valid images."""
        Align = TextLabel.Align
        alignments = [
            Align.LEFT | Align.TOP,
            Align.CENTER,
            Align.RIGHT | Align.BOTTOM,
            Align.HCENTER | Align.TOP,
            Align.LEFT | Align.VCENTER,
        ]
        for align in alignments:
            label = TextLabel("Test", LaminatedTape36mm, font_path, align=align)
            label.prepare(height=100)
            assert isinstance(label.image, Image.Image)

    def test_text_label_with_imagefont(self, font_path: str) -> None:
        """Test TextLabel initialization with ImageFont object."""
        font = ImageFont.truetype(font_path, size=24)
        label = TextLabel("Hello", LaminatedTape36mm, font)
        assert label.font is font
        label.prepare(height=100)
        assert isinstance(label.image, Image.Image)

    def test_text_label_with_min_width_mm(self, font_path: str) -> None:
        """Test TextLabel with min_width_mm parameter."""
        label = TextLabel("X", LaminatedTape36mm, font_path, min_width_mm=50.0)
        assert label.min_width_mm == 50.0
        label.prepare(height=100, resolution_dpi=180)
        # 50mm at 180 DPI = 50 * 180 / 25.4 ≈ 354 pixels minimum
        assert label.image.width >= 354

    def test_text_label_invalid_font_type_raises_valueerror(self) -> None:
        """Test that invalid font type raises ValueError."""
        with pytest.raises(ValueError, match="font must be a path string or ImageFont"):
            TextLabel("Hello", LaminatedTape36mm, 123)  # type: ignore[arg-type]

    def test_text_label_font_size_with_imagefont_warns(self, font_path: str) -> None:
        """Test that font_size with ImageFont object raises RuntimeWarning."""
        font = ImageFont.truetype(font_path, size=24)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TextLabel("Hello", LaminatedTape36mm, font, font_size=48)
            assert len(w) == 1
            assert issubclass(w[0].category, RuntimeWarning)
            assert "font_size is ignored" in str(w[0].message)
