"""
This file was created for the SRRConverter project
License: GPLv3

Author: Zatarita
Decription:   Convert a texture DDS texture into another image type for ease of use in 
3D Modeling Software that doesn't support DDS DX10 textures
"""

from PIL import Image, UnidentifiedImageError
import logging

class TextureConverter:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            # Fallback to its own logger
            self.logger = logging.getLogger(TextureConverter.__name__)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            self.logger.addHandler(handler)
    
    def convertTexture(self, texture_in_path, texture_out_path, format="PNG") -> bool:
        """
        # Valid formats
        (Some excluded due to needing additional parameters/being ill suited for this purpose)
            - AVIF
            - BLP
            - BMP
            - DDS
            - DIB
            - EPS
            - ICNS
            - IM
            - MPO
            - PCX
            - PNG
            - PPM
            - QOI
            - SGI
            - SPIDER
            - TGA
            - TIFF
            - WebP
            - XBM
        # Errors
            - Internal PIL error on loading texture
            - Internal PIL error on saving texture
        # Returns
            - bool: True on success
        """
        try:
            with Image.open(texture_in_path) as image:
                image.save(texture_out_path, format)
            return True
        except FileNotFoundError:       # Bad path
            self.logger.error(f"Failed to locate file: {texture_in_path}")
            return False
        except UnidentifiedImageError:  # Bad input format
            self.logger.error(f"Failed to load file [{texture_in_path}] - Reason: Unsupported format")
            return False
        except TypeError:               # Bad output format
            self.logger.error(f"Failed to save file [{self.fmt}] - Reason: Unsupported Format")
            return False