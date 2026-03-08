from pathlib import Path
from SrrConv.CrystalDynamics.bigfile import BigFile
from SrrConv.CrystalDynamics.hash import hash_str

def hash_impl(args):
    """Given a string return it's hash"""
    print(hex(hash_str(args.string)), f" {args.string}")

def extract_file_impl(args):
    """
        Given a target BigFile and a filename or hash extract
        the data and store it in the specified outpath location
    """
    input = args.input
    bigfile = args.bigfile
    outpath = Path(args.outpath)
    no_paths = args.no_paths
    index_type = args.index_type

    bigfile = BigFile.from_file(bigfile)
    if index_type == "hash":
        data = bigfile.get_data_from_hash(int(input, 0x10))
    else:
        data = bigfile.get_data_from_string(input)
    final_path = ""

    if no_paths:
        final_path = outpath / Path(input).name
        outpath.mkdir(parents=True, exist_ok=True)
    else:
        final_path = outpath / input
        final_path.parent.mkdir(parents=True, exist_ok=True)

    with open(final_path, "wb") as file_out:
        if data:
            file_out.write(data)
        else:
            # TODO: Error getting data
            return None

def extract_all_w_manifest_cross_ref(args):
    """
        If the --known flag is not set any binary blob that is not
        present in the hash manifest file will be extracted using
        it's hash as it's name
    """
    input = args.input
    bigfile = args.bigfile
    outpath = Path(args.outpath)
    no_paths = args.no_paths
    bigfile = BigFile.from_file(bigfile)
    
    hash_map = {}

    # Create the literal hash map [hash : filename]
    manifest_lines = open(input, "r").readlines()
    for line in manifest_lines:
        name = line.replace('\n', '').replace('\r', '')
        hash_map[hash_str(name)] = name


    for hash in bigfile.entries.keys():
        if hash in hash_map.keys():
            name = hash_map[hash]
        else:
            name = f"{hex(hash)}.bin"

        data = bigfile.get_data_from_hash(hash)
        if data is None:    # Hash may be in a different big file
            continue

        if no_paths:
            final_path = outpath / Path(name).name
            outpath.mkdir(parents=True, exist_ok=True)
        else:
            final_path = outpath / name
            final_path.parent.mkdir(parents=True, exist_ok=True)

        with open(final_path, "wb") as file_out:
            file_out.write(data)


def extract_w_manifest_cross_ref(args):
    """
        If requested to only extract known files, (If --known flag set) 
        extract any file present in the BigFile that can be cross 
        referenced in the hash manifest
    """
    input = args.input
    bigfile = args.bigfile
    outpath = Path(args.outpath)
    no_paths = args.no_paths
    bigfile = BigFile.from_file(bigfile)

    manifest_lines = open(input, "r").readlines()
    for line in manifest_lines:
        name = line.replace('\n', '').replace('\r', '')
        data = bigfile.get_data_from_string(name)
        if data is None:
            continue

        if no_paths:
            final_path = outpath / Path(name).name
            outpath.mkdir(parents=True, exist_ok=True)
        else:
            final_path = outpath / name
            final_path.parent.mkdir(parents=True, exist_ok=True)

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