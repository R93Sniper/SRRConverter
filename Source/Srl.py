"""
This file was created for the SRRConverter project
License: GPLv3

Description: Defines the SRL file structure
Author: Zatarita
"""

from dataclasses import dataclass
from struct import unpack, pack
from pathlib import Path

class HeaderMismatch(Exception):
    """Exception raised for SRL header mismatch."""

    def __init__(self, got):
        self.message = "Passed file does not contain a valid header"
        self.got = got
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Expected: '0x14D5253' - Got: {self.got})"

SRL_SIGNATURE    = b"SRL\x02"

@dataclass
class Header:
    number_bones: int
    delay: int
    event_count: int
    speed: int

    @classmethod 
    def from_stream(cls, stream):
        header = stream.read(4)
        if header != SRL_SIGNATURE:
            print("Header Mismatch")
        return cls(*unpack("<4I", stream.read(0x10)))
    
    def to_stream(self, stream):
        stream.write(SRL_SIGNATURE)
        stream.write(pack("<4I", self.number_bones, self.delay, self.event_count, self.speed))
    
@dataclass
class MatrixRow:
    x: float
    y: float
    z: float
    w: float

    @classmethod
    def from_stream(cls, stream):
        return cls(*unpack("<4f", stream.read(0x10)))

    def to_stream(self, stream):
        stream.write(pack("4f", self.x, self.y, self.z, self.w))

@dataclass
class Matrix:
    values: list[MatrixRow]

    @classmethod
    def from_stream(cls, stream):
        values = [MatrixRow.from_stream(stream) for _ in range(3)]
        return cls(values)

    def to_stream(self, stream):
        self.position.to_stream(stream)
        self.rotation.to_stream(stream)
        self.scale.to_stream(stream)

@dataclass
class SRLCollection:
    bones: list[Matrix]

    @classmethod
    def from_stream(cls, stream, count: int):
            entries = [Matrix.from_stream(stream) for _ in range (count)]
            return cls(entries)
        
    def to_stream(self, stream):
        for entry in self.bones:
            entry.to_stream(stream)
    
@dataclass
class SRLFile:
    header: Header
    entries: list[SRLCollection]

    @classmethod
    def from_file(cls, path: Path):
        with open(path, "rb") as file:
            header = Header.from_stream(file)
            entries = [SRLCollection.from_stream(file, header.number_bones) for _ in range (header.event_count)]
            return cls(header, entries)
        
    def to_file(self, path: Path):
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, "wb") as file:
            self.header.to_stream(file)
            for entry in self.entries:
                entry.to_stream(file)