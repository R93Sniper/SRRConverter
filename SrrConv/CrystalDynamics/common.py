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
        "tga",  "tiff", "tga",
        "webp", "xbm"
    ]

def do_texture_convert(
        texture_in_path: Path, 
        texture_out_path: Path, 
        format: IMAGE_FMTS,
        logger: Logger
    ):
    if texture_out_path.parent:
        texture_out_path.parent.mkdir(exist_ok=True, parents=True)
    # try:
    with Image.open(texture_in_path) as image:
        image.save(texture_out_path, format)
    return True
    # except FileNotFoundError:       # Bad path
    #     logger.error(f"Failed to locate file: {texture_in_path}")
    #     return False
    # except UnidentifiedImageError:  # Bad input format
    #     logger.error(f"Failed to load file [{texture_in_path}] - Reason: Unsupported format")
    #     return False
    # except TypeError:               # Bad output format
    #     logger.error(f"Failed to save file [{format}] - Reason: Unsupported Format")
    #     return False