from pathlib import Path
from SrrConv.CrystalDynamics.bigfile import BigFile
from SrrConv.CrystalDynamics.hash import hash_str
from SrrConv import __version__
from SrrConv.FBX.srm_to_fbx import srm_to_fbx_gen1, srm_to_fbx_gen2
from SrrConv.CrystalDynamics.image import IMAGE_FMTS

from .log import init_log
from .default_properties import *

from typing import get_args

import logging
import pickle
import tempfile

def _determine_extension_from_bytes(data):
    """Determine the filetype extension utilizing the file signature"""
    match data[:3]:
        case b'DDS':
            return ".dds"
        case b"SRM":
            return ".srm"
    return ".bin"

def list_defaults_impl(args):
    """Lists the current default parameters stored inside of config.defaults"""
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.list_defaults")
    logger.debug(f"{args}")
    
    defaults = Path("./config.defaults")
    if not defaults.exists():
        logger.debug("No defaults file exists...Creating defaults")
        generate_new_defaults()

    logger.debug("Loading config defaults from path: ./config.defaults")
    with open("./config.defaults", "rb") as file:
        logger.info("Current defaults:")
        properties = pickle.load(file)
        for (name, value) in properties.items():
            logger.info(f"\t{name}: {value}")
    

def assign_default_impl(args):
    """Change a default's value if the default exists"""
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.assign_default_impl")
    logger.debug(f"{args}")

    key = args.default
    value = args.value.replace("\\", "/")

    if key == "image_format":
        if value not in get_args(IMAGE_FMTS):
            logger.error(f"Unsupported image format: {value}")
            return
    
    defaults = Path("./config.defaults")
    if not defaults.exists():
        logger.debug("No defaults file exists...Creating defaults")
        generate_new_defaults()

    properties = {}

    logger.debug("Loading config defaults from path: ./config.defaults")
    with open("./config.defaults", "rb") as filein:
        properties = pickle.load(filein)
        
        if key in properties:
            logger.info(f"Reassigning `{key}` to `{value}`")

            if isinstance(properties[key], Path):
                properties[key] = Path(value)
            else:
                properties[key] = value
        else:
            logger.error(f"Unable to find property: {key}")

    logger.debug("Saving updated config defaults to path: ./config.defaults")
    with open("./config.defaults", "wb") as fileout:
        pickle.dump(properties, fileout)

def hash_impl(args):
    """Given a string return it's hash"""
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.hash_impl")
    logger.debug(f"{args}")
    logger.info(f"{hex(hash_str(args.string))}\t{args.string}")


def _get_bigfile_data(big_path: str | Path, index_type: str, input: str, logger: logging.Logger) -> None | bytearray:
    """Retrieve data from a big file by hash or filename"""
    logger.info("Loading BigFile: {bigfile}")
    bigfile = BigFile.from_file(big_path)

    if index_type == "hash":
        logger.info("Attempting to get the data for entry with hash: {input}...")
        return bigfile.get_data_from_hash(int(input, 0x10))
    else:
        logger.info("Attempting to get the data for entry with name: {input}...")
        return bigfile.get_data_from_string(input)

def _prep_output_directory(input: str, outpath: Path, no_paths: bool, logger: logging.Logger):
    """Create the final file path and ensure it's parent directories exist"""
    final_path = ""

    if no_paths:
        logger.debug("No path flag is set")
        final_path = outpath / Path(input).name
        outpath.mkdir(parents=True, exist_ok=True)
    else:
        logger.debug("No path flag is not set")
        final_path = outpath / input
        final_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Final path is: {final_path}")
    return final_path

def extract_file_impl(args):
    """
        Given a target BigFile and a filename or hash extract
        the data and store it in the specified outpath location
    """
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.extract_file_impl")
    logger.debug(f"{args}")

    input = args.input
    allow_overwrite = args.allow_overwrite
    bigfile  = args.bigfile if args.bigfile else get_default_property("def_directory", logger) / "bigfilehd.dat"
    outpath  = Path(args.outpath) if args.outpath else Path(get_default_property("out_path", logger))
    no_paths = args.no_paths
    type = args.type

    final_path = _prep_output_directory(input, outpath, no_paths, logger)
    if final_path.exists() and not allow_overwrite:
        logger.warning("Cannot extract file: {final_path} - File exists and overwriting is disabled.")
        return

    data = _get_bigfile_data(bigfile, type, input, logger)
    if data == None:
        logger.error("Failed to load data from big file! Aborting...")
        return
    logger.info("Successfully loaded data from the BigFile")

    logger.info(f"Writing {hex(len(data))} bytes to: {final_path}")
    with open(final_path, "wb") as file_out:
        file_out.write(data)

    logger.info(f"Success!")

def _get_manifest_filenames(input: str, logger: logging.Logger):
    """Load the list of file name from the manifest file"""
    logger.info(f"Loading filenames from the manifest file: {input}")
    hash_map = {}

    manifest_lines = open(input, "r").readlines()
    for line in manifest_lines:
        name = line.replace('\n', '').replace('\r', '')
        hash_map[hash_str(name)] = name

    logger.debug(f"Loaded: {len(hash_map)} filenames")
    return hash_map

def extract_all_w_manifest_cross_ref(args):
    """
        Extracts all the files found in a BigFile.
        If a hash is encountered that doesn't match a file name in the
        manifest file. The hashes value will be converted to a string
        instead.

        If the --known flag is not set any binary blob that is not
        present in the hash manifest file will be extracted using
        it's hash as it's name
    """
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.extract_all_w_manifest_cross_ref")
    logger.debug(f"{args}")

    input    = args.input if args.input else get_default_property("hash_manifest", logger)
    bigfile  = args.bigfile if args.bigfile else get_default_property("def_directory", logger) / "bigfilehd.dat"
    outpath  = Path(args.outpath) if args.outpath else Path(get_default_property("out_path", logger))
    no_paths = args.no_paths
    allow_overwrite = args.allow_overwrite

    logger.info(f"Loading BigFile: {bigfile}")
    bigfile = BigFile.from_file(bigfile)
    
    hash_map = _get_manifest_filenames(input, logger)

    for hash in bigfile.entries.keys():
        data = bigfile.get_data_from_hash(hash)
        if data is None: # Not really possible, but it's proper to check for None
            logger.debug(f"Hash not found, skipping...")
            continue

        if hash in hash_map.keys():
            name = hash_map[hash]
        else:
            logger.debug(f"Hash miss [{hex(hash)[2:]}]")
            extension = _determine_extension_from_bytes(data)
            logger.debug(f"Hash determined filetypes as: {extension[1:]}")
            name = f"{hex(hash)[2:]}{extension}"

        final_path = _prep_output_directory(name, outpath, no_paths, logger)
        
        if final_path.exists() and not allow_overwrite:
            logger.warning("Cannot extract file: {final_path} - File exists and overwriting is disabled.")
            continue

        logger.info(f"{final_path}")
        with open(final_path, "wb") as file_out:
            file_out.write(data)

# TODO: Update
def extract_w_manifest_cross_ref(args):
    """
        If requested to only extract known files, (If --known flag set) 
        extract any file present in the BigFile that can be cross 
        referenced in the hash manifest
    """
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.extract_w_manifest_cross_ref")
    logger.debug(f"{args}")

    input    = args.input
    allow_overwrite = args.allow_overwrite
    bigfile  = args.bigfile if args.bigfile else get_default_property("def_directory", logger) / "bigfilehd.dat"
    outpath  = Path(args.outpath) if args.outpath else get_default_property("out_path", logger)
    no_paths = args.no_paths

    bigfile  = BigFile.from_file(bigfile)
    manifest_lines = open(input, "r").readlines()
    for line in manifest_lines:
        name = line.replace('\n', '').replace('\r', '')

        if no_paths:
            final_path = outpath / Path(name).name
            outpath.mkdir(parents=True, exist_ok=True)
        else:
            final_path = outpath / name
            final_path.parent.mkdir(parents=True, exist_ok=True)

        if final_path.exists() and not allow_overwrite:
            logger.warning("Cannot extract file: {final_path} - File exists and overwriting is disabled.")
            continue

        data = bigfile.get_data_from_string(name)
        if data is None:
            continue

        with open(final_path, "wb") as file_out:
            file_out.write(data)

def extract_manifest_impl(args):
    """
        Attempts to load a BigFile and Manifest file.
        If successful, extract all hashes present in manifest.
    """
    known = args.known_only

    # If known set (default)
    if not known:
        return extract_all_w_manifest_cross_ref(args)
    else:
        return extract_w_manifest_cross_ref(args)

def _get_texture_dir(args, logger: logging.Logger):
    texture_dir = args.texture_dir
    if args.game_dir:
        if args.texture_dir:
            logger.warning("Attempted to pass a relative and absolute path at the same time. Using absolute")
        match args.game_dir.lower():
            case "sr1": texture_dir = Path(get_default_property("sr_directory", logger)) / "1/TEX"
            case "sr2": texture_dir = Path(get_default_property("sr_directory", logger)) / "2/TEX"
    return texture_dir

def _get_input_dir(args, logger: logging.Logger):
    logger.info("Resolving input directory")
    input = Path(args.input)
    if input.exists():
        return input
    
    logger.debug("Path doesn't exist... Checking if game relative flag was set")
    if args.game_dir:
        match args.game_dir.lower():
            case "sr1": 
                logger.debug("Game relative flag SR1 set")
                root = Path(get_default_property("sr_directory", logger)) / "1/OBJECT"
            case "sr2": 
                logger.debug("Game relative flag SR2 set")
                root = Path(get_default_property("sr_directory", logger)) / "2/OBJECT"
            case _: return None

        game_relative_path = root / input

        if game_relative_path.exists():
            logger.debug(f"Path resolved: {game_relative_path}!")
            return game_relative_path
        else:
            logger.error(f"Unable to resolve retalive path: {game_relative_path}")
            return None
    else: 
        logger.error(f"Unable to resolve path: {input}")
        return None

def _determine_srm_version(srm_path: Path):
    data = open(srm_path, "rb").read(4)
    if data[-1] == 1:
        return 1
    if data[-1] == 8:
        return 2
    else:
        return None
    
def _convert_file_gen1(args, logger):
    input           = args.input
    allow_overwrite = args.allow_overwrite
    outpath         = args.outpath if args.outpath else (get_default_property("out_path", logger) / Path(input).stem).with_suffix(".fbx")
    image_format    = args.image_format if args.image_format else get_default_property("image_format", logger)
    
    resolved_input = _get_input_dir(args, logger)
    texture_dir = _get_texture_dir(args, logger)

    srm_to_fbx_gen1(resolved_input, outpath, image_format, texture_dir, allow_overwrite, logger) # type: ignore
    
def _convert_file_gen2(args, logger):
    texture_path = Path(args.texture_dir) if args.texture_dir else Path(get_default_property("def_directory", logger)) / "bigfilehd.dat"
    input = Path(args.input)
    outpath = Path(args.outpath) if args.outpath else (get_default_property("out_path", logger) / Path(input).stem / Path(input).stem).with_suffix(".fbx")
    image_format    = args.image_format if args.image_format else get_default_property("image_format", logger)
    allow_overwrite = args.allow_overwrite
    prevent_cleanup = args.prevent_cleanup

    if input.suffix.lower() != ".srm":
        return # TODO: Error fucker
    else:
        srm_to_fbx_gen2(input, texture_path, outpath, image_format, allow_overwrite, prevent_cleanup, logger)
        return

    data = _get_bigfile_data(texture_path, "string", args.input, logger)

    if data == None:
        return # Error srm not found
    
    # Extract SRM from bigfile
    srm_path = (outpath / Path(raw_input).stem).with_suffix(".srm")
    with open(srm_path, "wb") as file: 
        file.write(data)

    srm_to_fbx_gen2(srm_path, texture_path, (outpath / Path(input).stem).with_suffix(".fbx"), image_format, allow_overwrite, cleanup, logger)

def convert_file_impl(args):
    logger = init_log(args)
    logger.debug(f"SRRConv {__version__} - {__name__}.convert_file_impl")
    logger.debug(f"{args}")

    resolved_input = _get_input_dir(args, logger)
    if resolved_input == None:
        return # File not found
    
    if resolved_input.suffix.lower() != ".srm":
        return # error must be srm
    version = _determine_srm_version(resolved_input)
    
    if version == 1:
        return _convert_file_gen1(args, logger)
    else:
        return _convert_file_gen2(args, logger)
    
    # allow_overwrite = args.allow_overwrite
    # outpath         = args.outpath if args.outpath else get_default_property("out_path", logger) / Path(raw_input).stem
    # image_format    = args.image_format if args.image_format else get_default_property("image_format", logger)

    # if version == 1:
    #     texture_dir = _get_texture_dir(args, logger)
    #     srm_to_fbx_gen1(resolved_input, (outpath / Path(raw_input).stem).with_suffix(".fbx"), image_format, texture_dir, allow_overwrite, logger)
    # else:
    #     # If it's already a srm file do the thing
    #     if resolved_input.suffix.lower() == ".srm":
    #         srm_to_fbx_gen2(resolved_input, args.input, (outpath / Path(raw_input).stem).with_suffix(".fbx"), image_format, allow_overwrite, logger)
    #         return

    #     data = _get_bigfile_data(resolved_input, "string", args.input, logger)

    #     if data == None:
    #         return # Error srm not found
        
    #     # Extract SRM from bigfile
    #     srm_path = (outpath / Path(raw_input).stem).with_suffix(".srm")
    #     with open(srm_path, "wb") as file: 
    #         file.write(data)

    #     srm_to_fbx_gen2(resolved_input, args.input, (outpath / Path(raw_input).stem).with_suffix(".fbx"), image_format, allow_overwrite, logger)
