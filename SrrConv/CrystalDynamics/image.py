"""
This file was created for the SRRConverter project
License: GPLv3

Description: Texture conversion using Pillow
Author: Zatarita
"""

from pathlib import Path
from typing import Literal
from logging import Logger

from PIL import Image, UnidentifiedImageError

IMAGE_FMTS = Literal[
        "avif", "blp",  "bmp",
        "dds",  "dib",  "eps",
        "icns", "im" ,  "mpo",
        "pcx",  "png",  "ppm",
        "qoi",  "sgi",  "spider",
        "tga",  "tiff", "webp",
        "xbm"
    ]

def convert_image_data (
        texture_in_path: Path,
        texture_out_path: Path,
        format: IMAGE_FMTS,
        logger: Logger
    ) -> bool:
    """Convert a texture from one format to another.

    Args:
        texture_in_path:  Path to the source texture file.
        texture_out_path: Path where the converted texture will be saved.
        format:           Target image format (e.g. ``"dds"``, ``"png"``).
        logger:           Logger instance for error reporting.

    Returns:
        True on success, False on failure.
    """
    texture_out_path.parent.mkdir(exist_ok=True, parents=True)
    try:
        with Image.open(texture_in_path) as image:
            image.save(texture_out_path, format)
            return True
    except FileNotFoundError:
        logger.warning(f"Texture not found [{texture_in_path}] - skipping...")
        return False
    except UnidentifiedImageError:
        logger.error(f"Failed to load file [{texture_in_path}] - Reason: Unsupported format")
        return False
    except TypeError:
        logger.error(f"Failed to save file [{format}] - Reason: Unsupported Format")
        return False