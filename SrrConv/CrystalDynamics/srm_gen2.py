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

from .srm_gen1 import Texture, MaterialPalette, Bones

class HeaderMismatch(Exception):
    """Exception raised for SRM header mismatch."""

    def __init__(self, got):
        self.message = "Passed file does not contain a valid header"
        self.got = got
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Expected: '0x84d5253' - Got: {self.got})"

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
    unknown_01    : int   = 0   # bone target 4 maybe?
    bone_weight_1 : int   = 0
    bone_weight_2 : int   = 0
    bone_weight_3 : int   = 0
    unknown_02    : int   = 0   # bone weight 4 maybe?
    u             : float = 0 
    v             : float = 0 

    @classmethod
    def from_stream(cls, stream) -> "Vertex":
        """ Parse vertex data from stream """
        vertex = cls(*unpack("<3f16B2f", stream.read(36)))
        vertex.normal_x -= 127
        vertex.normal_y -= 127
        vertex.normal_z -= 127
        vertex.texture_index += 1
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

SRM_SIGNATURE = 0x84d5253 #SRM\x08
@dataclass
class Header:
    """ Header for the SRM file """
    signature: int = SRM_SIGNATURE
    srm_lod: int = 0

    @classmethod
    def from_stream(cls, stream) -> "Header":
        """ Parse the header from stream. """
        (signature, srm_count) = unpack("<2I", stream.read(8))
        if signature != SRM_SIGNATURE:
            raise HeaderMismatch(signature)
        
        stream.read(0x10) # Maybe bounding box?
        return cls(signature, srm_count)

@dataclass
class SrmEntry:
    material_palette: MaterialPalette
    bones: Bones
    display_buffer: DisplayBuffer

    @classmethod
    def from_stream(cls, stream):
        count = int.from_bytes(stream.read(4), "little")
        stream.read(count * 0x74) # Burn extra data for now
        
        mat_pal = MaterialPalette.from_stream(stream)
        bones = Bones.from_stream(stream)
        dis_buf = DisplayBuffer.from_stream(stream)

        return cls(mat_pal, bones, dis_buf)
    
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

@dataclass
class SrmFile:
    """ Highest level structure, pulls all the parts together """
    header: Header
    entries: list[SrmEntry]

    @classmethod
    def from_file(cls, path: str | Path) -> "SrmFile":
        """ Attempt to parse a srm file """        
        with open(path, "rb") as stream:
            header: Header = Header.from_stream(stream)
            entries = [SrmEntry.from_stream(stream) for _ in range(header.srm_lod)]

        return cls(header, entries)
