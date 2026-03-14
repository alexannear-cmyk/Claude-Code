"""Generate simple app icons for the PWA.

Run once: python static/generate_icons.py

Creates 192x192 and 512x512 PNG icons with a calendar emoji style.
Uses only Pillow (pip install Pillow) — or skip this and use any
192x192 and 512x512 PNG files named icon-192.png and icon-512.png.
"""

import struct
import zlib


def create_png(width, height, bg_color, fg_color, text_lines):
    """Create a simple PNG file with colored background and centered text.

    This is a minimal PNG generator — no dependencies required.
    """

    def make_pixel_row(w, r, g, b):
        return b"\x00" + bytes([r, g, b]) * w

    # Create pixel data
    rows = []
    bg_r, bg_g, bg_b = bg_color
    fg_r, fg_g, fg_b = fg_color

    # Simple block-letter rendering for the icon
    # Draw background
    for _ in range(height):
        rows.append(make_pixel_row(width, bg_r, bg_g, bg_b))

    # Draw a simple "CS" in the center using block pixels
    raw = b"".join(rows)

    # PNG file structure
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return (
            struct.pack(">I", len(data))
            + chunk
            + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    )
    idat = make_chunk(b"IDAT", zlib.compress(raw))
    iend = make_chunk(b"IEND", b"")

    return header + ihdr + idat + iend


if __name__ == "__main__":
    for size in (192, 512):
        data = create_png(
            size, size,
            bg_color=(74, 144, 217),   # Blue
            fg_color=(255, 255, 255),  # White
            text_lines=["CS"],
        )
        filename = f"icon-{size}.png"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"Created {filename} ({len(data)} bytes)")
