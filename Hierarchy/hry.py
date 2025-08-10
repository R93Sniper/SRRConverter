"""
This file was created for the SRRConverter project
License: GPLv3

Author: Zatarita
Description: 
Skeleton hierarchy data isn't required for the game to utilize a skeleton, it is
a tool used to help animators constrain child bones during creation of animations.
When the SRM files get compiled that information isn't retained in the output format.
To combat this, the .hry format was created. The hry file will supply the parent child
relationship for bones. In order for it to do that we, as people, must look at the skeleton
and create the hierachy. That is done using a yaml file, the definition of which is simple

Filename: <NameOfFile.SRM>
Version: 1                  # In case of future revisions
Bones:
  <NameOfBone>:
    Index: 0
    Parent: Null
  <NameOfNextBone>:
    Index: 1
    Parent: 0

Where a Null bone indicates the intended root bone for the skeleton

This file will take a collection of these yaml definitions and spit out a .hry file.
This .hry file will then be used when converting SRM files to supply the propery hierarchy format.

In future versions - hopefully if custom models are possible, a .hry file should be created with
a compiled SRM.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
# import struct
from io import BytesIO

class MissingYamlEntry(Exception):
    """Exception raised for YAML missing expected entry."""

    def __init__(self, parent, expectation):
        self.message = "Yaml file is missing an expected YAML entry:"
        self.parent = parent
        self.expectation = expectation
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} {self.parent}.{self.expectation}"

@dataclass
class HryBone:
    name: str = ""
    parent: int = 0
    
    def to_file(self, stream):
        stream.write(len(self.name).to_bytes(1, "little"))
        stream.write(self.name.encode("ascii"))
        if self.parent is not None:
            stream.write(self.parent.to_bytes(1, "little"))
        else:
            stream.write(b'\xFF')

    @classmethod
    def from_stream(cls, file):
        ret = cls()
        ret.name = file.read(int.from_bytes(file.read(1), "little")).decode("ascii")
        ret.parent = int.from_bytes(file.read(1), "little")
        if ret.parent == 0xFF:
            ret.parent = None
        return ret

HRY_ENTRY_SIG = b'hre\x00'
@dataclass
class HryEntry:
    name: str = ""
    version: int = 0
    bones: dict[int, HryBone] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path):
        with open(path, "r") as file:
            ret = cls()
            yaml_data = yaml.safe_load(file)

            if "Filename" not in yaml_data:
                raise MissingYamlEntry("Filename", "")
            if "Version" not in yaml_data:
                raise MissingYamlEntry("Version", "")
            if "Bones" not in yaml_data:
                raise MissingYamlEntry("Bones", "")
            
            ret.name = yaml_data["Filename"]
            ret.version = yaml_data["Version"]
            
            for bone in yaml_data["Bones"]:
                if not "ID" in yaml_data["Bones"][bone]:
                    raise MissingYamlEntry(f"Bones.{bone}", "ID")
                if not "Parent" in yaml_data["Bones"][bone]:
                    raise MissingYamlEntry(f"Bones.{bone}", "Parent")
                ret.bones[yaml_data["Bones"][bone]["ID"]] = HryBone(bone, yaml_data["Bones"][bone]["Parent"])
        return ret
    
    def to_stream(self, stream):
        stream.write(HRY_ENTRY_SIG)
        stream.write(self.version.to_bytes(1, "little"))
        stream.write(len(self.name).to_bytes(1, "little"))
        stream.write(self.name.encode("ascii"))
        stream.write(len(self.bones).to_bytes(1, "little"))

        for id, bone in self.bones.items():
            stream.write(id.to_bytes(1, "little"))
            bone.to_file(stream)
            
    @classmethod
    def from_stream(cls, file):
        ret = cls()
        sig = file.read(4)
        if sig != HRY_ENTRY_SIG:
            print("Header mismatch!")
        ret.version = int.from_bytes(file.read(1), "little")
        ret.name = file.read(int.from_bytes(file.read(1), "little")).decode("ascii")
        bone_count = int.from_bytes(file.read(1), "little")
        for _ in range(bone_count):
            id = int.from_bytes(file.read(1), "little")
            bone = HryBone.from_stream(file)
            ret.bones[id] = bone
        return ret

HRY_SIG = b'hry\x00'
@dataclass
class HryFile:
    definitions: dict[str, HryEntry] = field(default_factory=dict)

    def import_yaml(self, path: Path):
        new_entry = HryEntry.from_yaml(path)
        self.definitions[new_entry.name] = new_entry

    def to_file(self, path: Path):
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, "wb") as file:
            offset_table = BytesIO()
            data = BytesIO()
            file.write(HRY_SIG)
            file.write(len(self.definitions).to_bytes(2, "little"))
            for definition in self.definitions.values():
                file.write(len(definition.name).to_bytes(1, "little"))
                file.write(definition.name.encode("ascii"))
            first_offset = file.tell() + (4 * len(self.definitions))
            for definition in self.definitions.values():
                offset_table.write((len(data.getbuffer()) + first_offset).to_bytes(4, "little"))
                definition.to_stream(data)
            file.write(offset_table.getbuffer())
            file.write(data.getbuffer())


    @classmethod
    def from_file(cls, path: Path):
        with open(path, "rb") as file:
            ret = cls()
            sig = file.read(4)
            if sig != HRY_SIG:
                print("Header mismatch!")
            count = int.from_bytes(file.read(2), "little")
            filenames = [file.read(int.from_bytes(file.read(1), "little")).decode("ascii") for _ in range(count)]
            offsets = [int.from_bytes(file.read(4), "little") for _ in range(count)]
            for i in range(count):
                file.seek(offsets[i])
                ret.definitions[filenames[i]] = HryEntry.from_stream(file)
        return ret
    
DEFINITIONS_PATH = Path("Definitions")
DEFINITIONS_FILE = Path("hierarchy_information.hry")

def load_definitions():
    print("Checking for existing hierarchy definition file...")
    if not DEFINITIONS_FILE.exists():
        print("\tExisting hry not found - Creating a new one")
        return HryFile()
    else:
        print(f"\tExisting hry found - Loading {DEFINITIONS_FILE}")
        return HryFile.from_file(DEFINITIONS_FILE)

def build_definitions():
    print("Building skeleton hierarchy definiton file...")
    if not DEFINITIONS_PATH.exists():
        print("Definitions folder does not exist! Please place all yaml files in a folder named 'Definitions'")
        return
    
    hry_file = load_definitions()
    
    print("Importing new definitions...")
    yaml_files = [f for f in DEFINITIONS_PATH.iterdir() if f.is_file() and f.suffix.lower() in [".yml", ".yaml"]]
    for yaml_file in yaml_files:
        print(f"\tImporting {yaml_file}: ", end="")
        try:
            hry_file.import_yaml(yaml_file)
            print("Done!")
        except Exception as e:
            print(f"Failed - {e}")

    
    print("Saving hry file")
    hry_file.to_file(DEFINITIONS_FILE)