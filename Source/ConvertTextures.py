"""
This file was created for the SRRConverter project
License: GPLv3

Author: Zatarita
Decription:   Convert a texture DDS texture into another image type for ease of use in 
3D Modeling Software that doesn't support DDS DX10 textures
"""

from PIL import Image

class ConvertTextures:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            # Fallback to its own logger
            import logging
            self.logger = logging.getLogger("ConvertTextures")
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
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
                image.save(texture_out_path, format=format)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to convert {texture_in_path} -> {texture_out_path}: {e}")
            return False