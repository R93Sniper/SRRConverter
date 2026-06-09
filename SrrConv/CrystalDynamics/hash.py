"""
This file was created for the SRRConverter project
License: GPLv3

Description: Implementation of the SR3 hash algorithm (CRC-32 variant)
Author: Zatarita
"""

from ctypes import c_uint32, c_int32
import pickle
from pathlib import Path

XOR_VALUE = 0x4c11db7
_CRC_TABLE_PATH = Path("./hash.crc_table")

def _build_crc_table() -> list[int]:
    """Build the CRC-32 lookup table for byte-wise processing."""
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ XOR_VALUE) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table


def _load_crc_table() -> list[int]:
    """Load the CRC table from disk cache, or build and cache it."""
    if _CRC_TABLE_PATH.exists():
        with open(_CRC_TABLE_PATH, "rb") as f:
            return pickle.load(f)
    table = _build_crc_table()
    with open(_CRC_TABLE_PATH, "wb") as f:
        pickle.dump(table, f)
    return table


CRC_TABLE = _load_crc_table()


def hash_str_fast(string: str) -> int:
    """Optimized hash using a precomputed CRC lookup table."""
    crc = 0xFFFFFFFF
    string = string.lower()
    for char in string:
        byte = ord(char)
        index = ((crc >> 24) ^ byte) & 0xFF
        crc = ((crc << 8) ^ CRC_TABLE[index]) & 0xFFFFFFFF
    return ~crc & 0xFFFFFFFF


def hash_str(string: str) -> int:
    """Original bitwise CRC-32 variant hash (kept for reference)."""
    b = c_uint32(0xFFFFFFFF)
    string = string.lower()
    
    for character in string:
        value = ord(character)
        b.value = b.value ^ value << 0x18
        backup = c_uint32(b.value * 2)
        a = c_uint32(backup.value ^ XOR_VALUE)
        if -1 < c_int32(b.value).value:
            a = backup
        
        b.value = a.value * 2 ^ XOR_VALUE
        if -1 < c_int32(a.value).value:
            b.value = a.value * 2
        
        a.value = b.value * 2 ^ XOR_VALUE
        if -1 < c_int32(b.value).value:
            a.value = b.value * 2

        b.value = a.value * 2 ^ XOR_VALUE
        if -1 < c_int32(a.value).value:
            b.value = a.value * 2

        a.value = b.value * 2 ^ XOR_VALUE
        if -1 < c_int32(b.value).value:
            a.value = b.value * 2

        b.value = a.value * 2 ^ XOR_VALUE
        if -1 < c_int32(a.value).value:
            b.value = a.value * 2

        a.value = b.value * 2 ^ XOR_VALUE
        if -1 < c_int32(b.value).value:
            a.value = b.value * 2

        b.value = a.value * 2 ^ XOR_VALUE
        if -1 < c_int32(a.value).value:
            b.value = a.value * 2
    b.value = ~b.value
    return b.value