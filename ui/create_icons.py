"""
Icon Generator for HA Bridge Control UI
Creates simple colored circle icons for system tray
"""

from PIL import Image, ImageDraw
import os
from pathlib import Path


def create_circle_icon(size: int, color: str, filename: str):
    """Create a simple colored circle icon"""
    # Create image with transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw circle
    margin = 2
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

    # Save icon
    img.save(filename, "PNG")
    print(f"Created icon: {filename}")


def create_all_icons():
    """Create all required icons"""
    icons_dir = Path("ui/assets/icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    # Icon colors
    colors = {
        "active": "#4ec9b0",  # Teal/green for running
        "inactive": "#f48771",  # Red for stopped
        "unknown": "#808080",  # Gray for unknown
    }

    # Create icons
    for status, color in colors.items():
        filename = icons_dir / f"tray_icon_{status}.png"
        create_circle_icon(16, color, filename)

    print("All icons created successfully!")


if __name__ == "__main__":
    create_all_icons()
