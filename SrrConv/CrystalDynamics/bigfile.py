"""
This file was created for the SRRConverter project
License: GPLv3

Description: Parser for Crystal Dynamics BigFile archives
Author: Zatarita
"""

from struct import unpack, pack
from dataclasses import dataclass
from typing import BinaryIO
from pathlib import Path

from SrrConv.CrystalDynamics.hash import hash_str

_MAX_FILE_ENTRIES = 0x100000

@dataclass
class FileTableEntry:
    """A single entry in the BigFile file table."""

    size: int
    offset: int
    unknown: int  # maybe compressed size on some consoles?

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "FileTableEntry":
        """Read one entry from an open BigFile stream."""
        return cls(*unpack("<3Q", stream.read(0x18)))

    def to_stream(self, stream: BinaryIO) -> None:
        """Write this entry back to a stream."""
        stream.write(pack("<3Q", self.size, self.offset, self.unknown))


class BigFile:
    """Lazy reader for Crystal Dynamics BigFile archives.

    Opens the file on construction and reads data on demand via seek/read.
    Use as a context manager to ensure the file is closed:

        with BigFile.from_file("path.big") as bf:
            data = bf.get_data_from_string("some/file.ext")
    """

    def __init__(self) -> None:
        self.entries: dict[int, FileTableEntry] = {}
        self.stream: BinaryIO | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "BigFile":
        """Open a BigFile and parse its file table.

        Raises ValueError if the entry count is zero or exceeds
        _MAX_FILE_ENTRIES. On any parse error the file handle is
        closed before the exception propagates.
        """
        ret = cls()
        ret.stream = open(path, "rb")

        try:
            count = int.from_bytes(ret.stream.read(4), "little")
            if count == 0 or count > _MAX_FILE_ENTRIES:
                raise ValueError(f"invalid file entry count: {count}")
            hashes = list(unpack(f"<{count}I", ret.stream.read(4 * count)))
            filetable = [FileTableEntry.from_stream(ret.stream) for _ in range(count)]

            for (file_hash, file_entry) in zip(hashes, filetable):
                ret.entries[file_hash] = file_entry
        except Exception:
            ret.stream.close()
            raise

        return ret

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "BigFile":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying stream if open."""
        if self.stream is not None:
            self.stream.close()

    def get_data_from_hash(self, file_hash: int) -> bytes:
        """Read the file data identified by *file_hash*.

        Raises ValueError if the archive was not opened from a file.
        Raises KeyError if the hash does not appear in the file table.
        """
        if self.stream is None:
            raise ValueError("BigFile not initialized from a file")

        if file_hash not in self.entries:
            raise KeyError(f"hash {file_hash:#010x} not found in archive")

        self.stream.seek(self.entries[file_hash].offset)
        return self.stream.read(self.entries[file_hash].size)

    def get_data_from_string(self, string: str) -> bytes:
        """Hash *string* and return the matching file data."""
        file_hash = hash_str(string)
        return self.get_data_from_hash(file_hash)
