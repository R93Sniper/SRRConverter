import pickle
from pathlib import Path 

DEFAULT_PROPERTIES = {
    "hash_manifest": Path("./hash.manifest"),
    "log_file": Path("./output.log"),
    "out_path": Path("./"),
    "image_format": "dds",
    "sr_directory": Path("C:/Program Files (x86)/Steam/steamapps/common/Soul Reaver I-II/"),
    "def_directory": Path("C:/Program Files (x86)/Steam/steamapps/common/Legacy of Kain Defiance Remastered/"),
    "log_level": "info"
}

def get_default_property(property, logger):
    """Return a default property if one exists"""
    defaults = Path("./config.defaults")
    if not defaults.exists():
        if logger: logger.debug("No defaults file exists...Creating defaults")
        generate_new_defaults()

    if logger: logger.debug(f"Loading {property} default from path: ./config.defaults")
    with open("./config.defaults", "rb") as file:
        properties = pickle.load(file)
        if property not in properties:
            if logger: logger.error("No property `{property}` found in defaults")
        return properties.get(property, None)

def generate_new_defaults():
    """When no config.defaults exists, create them"""
    with open("config.defaults", "wb") as fileout:
        pickle.dump(DEFAULT_PROPERTIES, fileout)