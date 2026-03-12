from struct import unpack, pack
from dataclasses import dataclass
from SrrConv.CrystalDynamics.hash import hash_str

from pathlib import Path

@dataclass
class FileTableEntry:
    size: int
    offset: int
    unknown: int # maybe compressed size on some consoles? 8 bytes

    @classmethod
    def from_stream(cls, stream) -> "FileTableEntry":
        return cls(*unpack("<3Q", stream.read(0x18)))
    
    # May be needed someday? easy to knock out now
    def to_stream(self, stream):
        stream.write(pack("<3Q", self.offset, self.size, self.unknown))

class BigFile:
    def __init__(self) -> None:
        self.entries = {}
        self.stream = None

    @classmethod
    def from_file(cls, path: str | Path) -> "BigFile":
        ret = cls()
        ret.stream = open(path,  "rb")

        count = int.from_bytes(ret.stream.read(4), "little")
        hashes = list(unpack(f"<{count}I", ret.stream.read(4 * count)))
        filetable = [FileTableEntry.from_stream(ret.stream) for _ in range(count)]

        for (hash, file_entry) in zip(hashes, filetable):
            ret.entries[hash] = file_entry

        return ret
    
    def get_data_from_hash(self, hash: int):
        if self.stream == None:
            # TODO: Error uninitialized bigfile
            return None
        
        if hash in self.entries.keys():
            self.stream.seek(self.entries[hash].offset)
            return self.stream.read(self.entries[hash].size)
        else:
            # TODO: Error No match
            return None
        
    def get_data_from_string(self, string: str):
        hash = hash_str(string)
        return self.get_data_from_hash(hash)