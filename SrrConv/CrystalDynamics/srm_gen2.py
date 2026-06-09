"""
This file was created for the SRRConverter project
License: GPLv3

Description: Defines the SRM file structure for Defiance Remastered (Gen2)
Author: Zatarita
"""

from dataclasses import dataclass
from struct import unpack
from pathlib import Path
from typing import BinaryIO

from SrrConv.CrystalDynamics.srm_gen1 import MaterialPalette, Bones

NORMAL_BIAS = 127
VERTEX_STRIDE = 36
SRM_SIGNATURE = 0x84D5253  # SRM\x08

class HeaderMismatch(Exception):
    """Exception raised for SRM header mismatch."""

    def __init__(self, got: int) -> None:
        self.message = "Passed file does not contain a valid header"
        self.got = got
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.message} (Expected: '0x84D5253' - Got: {self.got})"

@dataclass(unsafe_hash=True)
class Vertex:
    """Vertex data for a single vertex in the model."""
    x: float = 0
    z: float = 0
    y: float = 0
    extra_1: int = 0
    extra_2: int = 0
    extra_3: int = 0
    extra_4: int = 0
    normal_x: int = 0
    normal_y: int = 0
    normal_z: int = 0
    texture_index: int = 0
    bone_target_1: int = 0
    bone_target_2: int = 0
    bone_target_3: int = 0
    unknown_01: int = 0
    bone_weight_1: int = 0
    bone_weight_2: int = 0
    bone_weight_3: int = 0
    unknown_02: int = 0
    u: float = 0
    v: float = 0

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "Vertex":
        """Parse vertex data from stream, recentering normals from [0, 255] to [-127, 128]."""
        vertex = cls(*unpack("<3f16B2f", stream.read(VERTEX_STRIDE)))
        vertex.normal_x -= NORMAL_BIAS
        vertex.normal_y -= NORMAL_BIAS
        vertex.normal_z -= NORMAL_BIAS
        # TODO: determine why texture_index is offset by +1 in Gen2
        vertex.texture_index += 1
        return vertex

@dataclass
class DisplayBuffer:
    """Holds all the vertices and indices (the mesh geometry)."""
    vertices: list[Vertex]
    indices: list[tuple[int, int, int]]

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "DisplayBuffer":
        """Parse the vertices and indices from stream."""
        (vert_count, index_count) = unpack("<2I", stream.read(8))
        # TODO: enforce a reasonable upper bound on vert_count and index_count
        vertices = [Vertex.from_stream(stream) for _ in range(vert_count)]
        indices  = [unpack("<3H", stream.read(6)) for _ in range(index_count // 3)]

        return cls(vertices, indices)

    def num_vertices(self) -> int:
        return len(self.vertices)

    def num_triangles(self) -> int:
        return len(self.indices)

@dataclass
class Header:
    """Header for the SRM file."""
    signature: int = SRM_SIGNATURE
    srm_lod: int = 0

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "Header":
        """Parse the header from stream."""
        (signature, srm_lod) = unpack("<2I", stream.read(8))
        if signature != SRM_SIGNATURE:
            raise HeaderMismatch(signature)

        stream.read(0x10)  # Maybe bounding box?
        return cls(signature, srm_lod)

@dataclass
class SrmEntry:
    """A single LOD entry within a Gen2 SRM file."""
    material_palette: MaterialPalette
    bones: Bones
    display_buffer: DisplayBuffer

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "SrmEntry":
        """Parse a LOD entry from stream."""
        count = int.from_bytes(stream.read(4), "little")
        # TODO: enforce a reasonable upper bound on count
        stream.read(count * 0x74)

        material_palette = MaterialPalette.from_stream(stream)
        bones = Bones.from_stream(stream)
        display_buffer = DisplayBuffer.from_stream(stream)

        return cls(material_palette, bones, display_buffer)

    def get_vertices(self) -> list[tuple[float, float, float]]:
        return [(vert.x, vert.y, -vert.z) for vert in self.display_buffer.vertices]

    def get_normals(self) -> list[tuple[float, float, float]]:
        return [(float(vert.normal_x), float(vert.normal_y), float(vert.normal_z)) for vert in self.display_buffer.vertices]

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
    """Top-level structure containing all Gen2 SRM LOD entries."""
    header: Header
    entries: list[SrmEntry]

    @classmethod
    def from_file(cls, path: str | Path) -> "SrmFile":
        """Attempt to parse a Gen2 SRM file from *path*."""
        with open(path, "rb") as stream:
            header: Header = Header.from_stream(stream)
            entries = [SrmEntry.from_stream(stream) for _ in range(header.srm_lod)]

        return cls(header, entries)
