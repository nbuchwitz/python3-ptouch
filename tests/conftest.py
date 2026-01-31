# SPDX-FileCopyrightText: 2024-2026 Nicolai Buchwitz <nb@tipi-net.de>
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared test fixtures for ptouch tests."""

import pytest
from PIL import Image

from ptouch import (
    LaminatedTape6mm,
    LaminatedTape12mm,
    LaminatedTape24mm,
    LaminatedTape36mm,
)
from ptouch.connection import Connection


class MockConnection(Connection):
    """Mock connection that captures data sent to the printer."""

    def __init__(self) -> None:
        self.data: bytes = b""
        self.closed = False
        self.connected = False

    def connect(self, printer: object) -> None:
        """Mock connect - just mark as connected."""
        del printer  # unused
        self.connected = True

    def write(self, payload: bytes) -> None:
        """Capture data instead of sending it."""
        self.data += payload

    def close(self) -> None:
        """Mark connection as closed."""
        self.closed = True


@pytest.fixture
def mock_connection() -> MockConnection:
    """Provide a mock connection for testing."""
    return MockConnection()


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a simple test image."""
    img = Image.new("RGB", (100, 50), color=(255, 255, 255))
    return img


@pytest.fixture
def sample_image_with_content() -> Image.Image:
    """Create a test image with some black content."""
    img = Image.new("RGB", (100, 50), color=(255, 255, 255))
    # Draw a black rectangle in the center
    for x in range(25, 75):
        for y in range(10, 40):
            img.putpixel((x, y), (0, 0, 0))
    return img


@pytest.fixture
def tape_6mm() -> LaminatedTape6mm:
    """Provide a 6mm laminated tape instance."""
    return LaminatedTape6mm()


@pytest.fixture
def tape_12mm() -> LaminatedTape12mm:
    """Provide a 12mm laminated tape instance."""
    return LaminatedTape12mm()


@pytest.fixture
def tape_24mm() -> LaminatedTape24mm:
    """Provide a 24mm laminated tape instance."""
    return LaminatedTape24mm()


@pytest.fixture
def tape_36mm() -> LaminatedTape36mm:
    """Provide a 36mm laminated tape instance."""
    return LaminatedTape36mm()
