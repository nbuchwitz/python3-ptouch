# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tests for the ptouch.tape module."""

import pytest

from ptouch.tape import (
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


class TestTapeWidths:
    """Test tape width attributes."""

    @pytest.mark.parametrize(
        "tape_class,expected_width",
        [
            (LaminatedTape6mm, 6),
            (LaminatedTape9mm, 9),
            (LaminatedTape12mm, 12),
            (LaminatedTape18mm, 18),
            (LaminatedTape24mm, 24),
            (LaminatedTape36mm, 36),
        ],
    )
    def test_laminated_tape_width(
        self, tape_class: type[LaminatedTape], expected_width: int
    ) -> None:
        """Test that laminated tape classes have correct width_mm."""
        tape = tape_class()
        assert tape.width_mm == expected_width

    @pytest.mark.parametrize(
        "tape_class,expected_width",
        [
            (LaminatedTape6mm, 6),
            (LaminatedTape9mm, 9),
            (LaminatedTape12mm, 12),
            (LaminatedTape18mm, 18),
            (LaminatedTape24mm, 24),
            (LaminatedTape36mm, 36),
        ],
    )
    def test_tape_width_class_attribute(
        self, tape_class: type[LaminatedTape], expected_width: int
    ) -> None:
        """Test that width_mm is accessible as class attribute."""
        assert tape_class.width_mm == expected_width


class TestTapeInheritance:
    """Test tape class inheritance."""

    def test_laminated_tape_inherits_from_tape(self) -> None:
        """Test that LaminatedTape inherits from Tape."""
        assert issubclass(LaminatedTape, Tape)

    def test_heat_shrink_tape_inherits_from_tape(self) -> None:
        """Test that HeatShrinkTape inherits from Tape."""
        assert issubclass(HeatShrinkTape, Tape)

    @pytest.mark.parametrize(
        "tape_class",
        [
            LaminatedTape6mm,
            LaminatedTape9mm,
            LaminatedTape12mm,
            LaminatedTape18mm,
            LaminatedTape24mm,
            LaminatedTape36mm,
        ],
    )
    def test_laminated_tape_sizes_inherit_from_laminated_tape(
        self, tape_class: type[LaminatedTape]
    ) -> None:
        """Test that all laminated tape sizes inherit from LaminatedTape."""
        assert issubclass(tape_class, LaminatedTape)
        assert issubclass(tape_class, Tape)


class TestTapeInstantiation:
    """Test tape instantiation."""

    @pytest.mark.parametrize(
        "tape_class",
        [
            LaminatedTape6mm,
            LaminatedTape9mm,
            LaminatedTape12mm,
            LaminatedTape18mm,
            LaminatedTape24mm,
            LaminatedTape36mm,
        ],
    )
    def test_laminated_tape_can_be_instantiated(self, tape_class: type[LaminatedTape]) -> None:
        """Test that laminated tape classes can be instantiated."""
        tape = tape_class()
        assert isinstance(tape, tape_class)
        assert isinstance(tape, LaminatedTape)
        assert isinstance(tape, Tape)
