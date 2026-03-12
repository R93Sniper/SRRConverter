"""
This file was created for the SRRConverter project
License: GPLv3

Description: Defines the SRM file structure for SR1 and SR2
Author: Zatarita
"""

from dataclasses import dataclass
from struct import unpack
from enum import IntFlag
from pathlib import Path

class HeaderMismatch(Exception):
    """Exception raised for SRM header mismatch."""

    def __init__(self, got):
        self.message = "Passed file does not contain a valid header"
        self.got = got
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Expected: '0x14D5253' - Got: {self.got})"

SRM_SIGNATURE = 0x14D5253 #SRM\x01

@dataclass
class Header:
    """ Header for the SRM file """
    signature: int = SRM_SIGNATURE
    # a lot of unknowns here, but I don't care ATM

    @classmethod
    def from_stream(cls, stream) -> "Header":
        """ Parse the header from stream. """
        (signature, count) = unpack("<2I", stream.read(8))
        stream.read(count * 44) # Burn extra data for now
        if signature != SRM_SIGNATURE:
            raise HeaderMismatch(signature)
        return cls(signature)
    
class TextureType(IntFlag):
    """ Bitflag representing which maps are defined for a texture (EG diffuse, specular, etc) """
    Diffuse  = 0b0001
    Normal   = 0b0010
    Specular = 0b0100
    Emissive = 0b1000

    @classmethod
    def try_from(cls, stream) -> "TextureType":
        """ Try to read the TextureType from stream. If unknown flag encountered it will print out. soft warning """
        value = int.from_bytes(stream.read(1), "little")
        if value > 0xF:
            print(f"Unknown texture flag: {0b11110000 & value}")
        return TextureType(value)

@dataclass
class Texture:
    """ Represents an individual texture in the model. """
    name: str = ""
    type: TextureType = TextureType(0)

    @classmethod
    def from_stream(cls, stream) -> "Texture":
        """ Parse a texture entry from the texture palette """
        name: str = stream.read(31).decode("ascii").rstrip("\x00")
        type: TextureType = TextureType.try_from(stream)

        return cls(name, type)
    
    def get_texture_suffixes(self, extension: str = "") -> list[str | None]:
        """ Given the current texture type, create the suffixes that represent the expected filenames. """
        return [
            f"{self.name}_D{extension}" if TextureType.Diffuse in self.type else None,
            f"{self.name}_N{extension}" if TextureType.Normal in self.type else None,
            f"{self.name}_S{extension}" if TextureType.Specular in self.type else None,
            f"{self.name}_E{extension}" if TextureType.Emissive in self.type else None
        ]


@dataclass
class MaterialPalette:
    """ Holds all the textures used by the model """
    materials: list[Texture]

    @classmethod
    def from_stream(cls, stream) -> "MaterialPalette":
        """ Parse the texture palette from stream """
        count: int = int.from_bytes(stream.read(4), "little")
        return cls([Texture.from_stream(stream) for _ in range(count)])
    
@dataclass(unsafe_hash=True)
class Vertex:
    """ Vertex data """
    x             : float = 0
    z             : float = 0
    y             : float = 0
    extra_1       : int   = 0   # unknown
    extra_2       : int   = 0   # unknown
    extra_3       : int   = 0   # unknown
    extra_4       : int   = 0   # Usually [0, 2]
    normal_x      : int   = 0   # Should prolly be normalized x/255
    normal_y      : int   = 0   # Should prolly be normalized x/255
    normal_z      : int   = 0   # Should prolly be normalized x/255
    texture_index : int   = 0   # Weird it's on the vertex and not the face
    bone_target_1 : int   = 0
    bone_target_2 : int   = 0
    bone_target_3 : int   = 0
    u             : int   = 0   # Should prolly be normalized x/255
    bone_weight_1 : int   = 0
    bone_weight_2 : int   = 0
    bone_weight_3 : int   = 0
    v             : int   = 0   # Should prolly be normalized x/255

    @classmethod
    def from_stream(cls, stream) -> "Vertex":
        """ Parse vertex data from stream """
        vertex = cls(*unpack("<3f16B4x", stream.read(0x20)))
        vertex.normal_x -= 127
        vertex.normal_y -= 127
        vertex.normal_z -= 127
        return vertex

@dataclass
class DisplayBuffer:
    """ Last part of the file. Holds all the vertices and indices """
    vertices: list[Vertex]
    indices: list[tuple[int, int, int]]

    @classmethod
    def from_stream(cls, stream) -> "DisplayBuffer":
        """ Parse the vertices and indices from stream """
        (vert_count, index_count) = unpack("<2I", stream.read(8))
        vertices = [Vertex.from_stream(stream) for _ in range(vert_count)]
        indices  = [unpack("<3H", stream.read(6)) for _ in range(0, index_count, 3)]

        return cls(vertices, indices)
    
    def num_vertices(self):
        return len(self.vertices)
    
    def num_indices(self):
        return len(self.indices)
    
@dataclass
class Bones:
    bone_list: list[tuple[float, float, float]]
    active_bones: list[bool]

    @classmethod
    def from_stream(cls, stream) -> "Bones":
        face_bone_count: int = int.from_bytes(stream.read(4),"little")

        bone_list: list[tuple[float, float, float]] = [unpack("<3f", stream.read(0xc)) for _ in range(0x80)]

        # Unkown influences this data array size - Hacky fix for now
        if face_bone_count > 0:
            stream.read(face_bone_count * 0x30 + 4)

        active_bones: list[bool] = list(unpack("128?", stream.read(0x80)))

        bone_list = [bone_list[i] for i in range(0x80) if active_bones[i]]
        return cls(bone_list, active_bones)
    
@dataclass
class SrmFile:
    """ Highest level structure, pulls all the parts together """
    header: Header
    material_palette: MaterialPalette
    bones: Bones
    display_buffer: DisplayBuffer

    @classmethod
    def from_file(cls, path: str | Path) -> "SrmFile":
        """ Attempt to parse a srm file """        
        with open(path, "rb") as stream:
            header: Header = Header.from_stream(stream)
            texture_palette: MaterialPalette = MaterialPalette.from_stream(stream)
            bones: Bones = Bones.from_stream(stream)
            buffer: DisplayBuffer = DisplayBuffer.from_stream(stream)

        return cls(header, texture_palette, bones, buffer)
    
    def get_vertices(self) -> list[tuple[float, float, float]]:
        return [(vert.x, vert.y, -vert.z) for vert in self.display_buffer.vertices]
    
    def get_normals(self) -> list[tuple[float, float, float]]:
        return [(vert.normal_x, vert.normal_y, vert.normal_z) for vert in self.display_buffer.vertices]

    def get_vertex_bone_ids(self) -> list[tuple[int, int, int]]:
        return [
            (
                vert.bone_target_1, 
                vert.bone_target_2, 
                vert.bone_target_3
            ) for vert in self.display_buffer.vertices
        ]

    def get_vertex_weights(self) -> list[tuple[float, float, float]]:
        return [
            (
                vert.bone_weight_1 / 255.0, 
                vert.bone_weight_2 / 255.0, 
                vert.bone_weight_3 / 255.0
            ) for vert in self.display_buffer.vertices
        ]
    
    def get_bone_positions(self) -> list[tuple[float, float, float]]:
        return self.bones.bone_list
