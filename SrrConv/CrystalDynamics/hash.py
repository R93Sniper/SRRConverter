from ctypes import c_uint32, c_int32

XOR_VALUE = 0x4c11db7

def hash_str(string: str) -> int:
    b = c_uint32(0xFFFFFFFF)
    string = string.lower()
    
    for (index, character) in enumerate(string):
        value = ord(character)
        a = c_uint32(len(string) - index)
        b.value = b.value ^ value << 0x18
        backup = c_uint32(b.value * 2)
        a.value = backup.value ^ XOR_VALUE
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